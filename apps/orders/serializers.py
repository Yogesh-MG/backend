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
            'payment_method', 'items', 'subtotal', 'delivery_fee', 'total'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        with transaction.atomic():
            # 1. Create the Order
            order = Order.objects.create(user=user, **validated_data)

            # 2. Process Items and Stock
            for item in items_data:
                batch = item['batch']
                qty = item['quantity']

                # Atomic Stock Check
                if batch.stock_level < qty:
                    raise serializers.ValidationError(
                        f"Only {batch.stock_level} units of {batch.product.name} are available."
                    )

                # Deduct Stock
                batch.stock_level -= qty
                batch.save()

                # Create Order Item (Snapshotting price and name)
                OrderItem.objects.create(
                    order=order,
                    batch=batch,
                    product_name=batch.product.name,
                    price=batch.price,
                    quantity=qty,
                    unit=batch.product.unit
                )

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
