from rest_framework import serializers
from django.db import transaction
from apps.inventory.models import InventoryBatch
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['batch', 'quantity']

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'address_title', 'address_line', 'delivery_slot', 
            'payment_method', 'items', 'subtotal', 'delivery_fee', 'total', 'is_paid'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # Remove incoming prices to avoid conflict with backend calculations
        validated_data.pop('subtotal', None)
        validated_data.pop('delivery_fee', None)
        validated_data.pop('total', None)
        
        user = self.context['request'].user
        delivery_slot_type = validated_data.get('delivery_slot', 'EXPRESS')

        with transaction.atomic():
            # 1. Calculate Prices on Backend
            subtotal = 0
            order_items_to_create = []

            for item_data in items_data:
                batch = item_data['batch']
                qty = item_data['quantity']

                # Stock Check
                if batch.stock_level < qty:
                    raise serializers.ValidationError(f"Only {batch.stock_level} units of {batch.variant.product.name} are available.")

                item_price = batch.price
                subtotal += item_price * qty

                # Prepare item for creation (snapshotting)
                order_items_to_create.append({
                    'batch': batch,
                    'product_name': batch.variant.product.name,
                    'price': item_price,
                    'quantity': qty,
                    'unit': batch.variant.unit
                })

            # 2. Get Delivery Fee from actual slot config (or simple logic for now)
            # In a real app, you'd fetch the DeliverySlot model here.
            delivery_fee = 25 if subtotal < 199 else 0
            total = subtotal + delivery_fee

            # 3. Create the Order with calculated values
            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=total,
                **validated_data
            )

            # 4. Create items and deduct stock
            for item in order_items_to_create:
                batch = item.pop('batch')
                qty = item['quantity']
                
                batch.stock_level -= qty
                batch.save()
                
                OrderItem.objects.create(order=order, batch=batch, **item)

            return order

class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'

    def get_items(self, obj):
        items = obj.items.all()
        return [
            {
                "product_name": i.product_name,
                "price": float(i.price),
                "quantity": i.quantity,
                "unit": i.unit,
                "total": float(i.price * i.quantity)
            } for i in items
        ]
