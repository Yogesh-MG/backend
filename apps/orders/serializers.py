from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from apps.inventory.models import InventoryBatch
from .models import Order, OrderItem

def get_organic_impact_data(order, user):
    """Get organic impact data, using prefetched cache when available to avoid N+1 queries."""
    from apps.wallet.models import CustomerImpact
    
    # Use the correct related_name 'impact' (OneToOneField)
    impact = None
    try:
        impact = user.impact
    except CustomerImpact.DoesNotExist:
        impact = None
    
    lifetime = {
        "water": float(impact.total_water) if impact else 0.0,
        "soil": float(impact.total_soil) if impact else 0.0,
        "chemical": float(impact.total_chemical) if impact else 0.0,
        "farmers": float(impact.total_farmer) if impact else 0.0,
        "healthy_orders": impact.total_orders if impact else 0
    }

    return {
        "current_order": {
            "water": float(order.order_water),
            "soil": float(order.order_soil),
            "chemical": float(order.order_chemical),
            "farmers": float(order.order_farmer)
        },
        "lifetime": lifetime,
        "message": "Your healthy choices continue supporting organic farming."
    }

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['batch', 'quantity']

class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/admin views - minimal nested data."""
    user_name = serializers.CharField(source='user.get_full_name')
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'tracking_id', 'user_name', 'status', 'total', 'delivery_slot', 'created_at', 'items_count']
    
    def get_items_count(self, obj):
        # Uses prefetched cache
        return obj.items.count()

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    organic_impact = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'tracking_id', 'address_title', 'address_line', 'delivery_slot', 
            'payment_method', 'items', 'subtotal', 'delivery_fee', 'total', 'is_paid',
            'wallet_amount_used', 'remaining_amount', 'organic_impact'
        ]
        read_only_fields = ['id', 'tracking_id', 'subtotal', 'delivery_fee', 'total']

    def get_organic_impact(self, obj):
        user = self.context['request'].user if 'request' in self.context else obj.user
        return get_organic_impact_data(obj, user)

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # Remove fields that might be passed twice (from perform_create or frontend)
        validated_data.pop('subtotal', None)
        validated_data.pop('delivery_fee', None)
        validated_data.pop('total', None)
        is_paid_passed = validated_data.pop('is_paid', False)
        wallet_amount_used_passed = validated_data.pop('wallet_amount_used', Decimal('0.00'))
        remaining_amount_passed = validated_data.pop('remaining_amount', Decimal('0.00'))
        validated_data.pop('member_discount', None)
        validated_data.pop('pride_limit_used', None)
        user = validated_data.pop('user', self.context['request'].user)
        delivery_slot_type = validated_data.get('delivery_slot', 'EXPRESS')

        with transaction.atomic():
            # 1. Calculate Prices on Backend
            subtotal = Decimal('0.00')
            order_items_to_create = []

            for item_data in items_data:
                batch = item_data['batch']
                qty = item_data['quantity']

                # Stock Check
                if batch.stock_level < qty:
                    raise serializers.ValidationError(f"Only {batch.stock_level} units of {batch.variant.product.name} are available.")

                item_price = batch.variant.price
                subtotal += item_price * qty

                # Prepare item for creation (snapshotting)
                order_items_to_create.append({
                    'batch': batch,
                    'product_name': batch.variant.product.name,
                    'price': item_price,
                    'purchase_price': batch.purchase_price,
                    'quantity': qty,
                    'unit': batch.variant.unit
                })

            # 2. Get Delivery Fee from actual slot config (or simple logic for now)
            delivery_fee = Decimal('25.00') if subtotal < Decimal('199.00') else Decimal('0.00')

            # 3. Apply PRIDE discount limit (if user has PRIDE partnership)
            from apps.wallet.models import Wallet
            member_discount = Decimal('0.00')
            pride_limit_used = Decimal('0.00')
            try:
                wallet = Wallet.objects.select_for_update().get(user=user)
                has_partnership = hasattr(user, 'partnership') and user.partnership and not user.partnership.refund_requested
                if has_partnership and wallet.accumulated_pride_limit > 0:
                    # How much MRP can be discounted?
                    discountable_mrp = min(subtotal, wallet.accumulated_pride_limit)
                    member_discount = (discountable_mrp * Decimal('0.30')).quantize(Decimal('0.01'))
                    pride_limit_used = discountable_mrp
                    # Deduct the MRP value that got discounted from the limit
                    wallet.accumulated_pride_limit -= discountable_mrp
                    wallet.save(update_fields=['accumulated_pride_limit'])
            except Wallet.DoesNotExist:
                pass

            total = subtotal + delivery_fee - member_discount

            # 4. Handle Wallet Payment Deduction
            payment_method = validated_data.get('payment_method', 'UPI')
            is_paid = is_paid_passed or (payment_method == 'WALLET')

            wallet_to_deduct = Decimal('0.00')
            if payment_method == 'WALLET':
                wallet_to_deduct = total
            elif payment_method in ['WALLET_UPI', 'WALLET_CARD']:
                wallet_to_deduct = wallet_amount_used_passed

            deducted_balance_before = None
            deducted_balance_after = None
            wallet_obj = None

            if wallet_to_deduct > 0:
                try:
                    wallet_obj = Wallet.objects.select_for_update().get(user=user)
                    if wallet_obj.balance < wallet_to_deduct:
                        raise serializers.ValidationError(f"Insufficient wallet balance. Required: ₹{wallet_to_deduct}, Available: ₹{wallet_obj.balance}")
                    
                    # Deduct balance atomically
                    deducted_balance_before = wallet_obj.balance
                    wallet_obj.balance -= wallet_to_deduct
                    wallet_obj.save(update_fields=['balance'])
                    deducted_balance_after = wallet_obj.balance
                    wallet_amount_used = wallet_to_deduct
                except Wallet.DoesNotExist:
                    raise serializers.ValidationError("No wallet found for this user. Please top up first.")
            else:
                wallet_amount_used = Decimal('0.00')

            # 5. Create the Order with calculated values
            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=total,
                member_discount=member_discount,
                pride_limit_used=pride_limit_used,
                wallet_amount_used=wallet_amount_used,
                remaining_amount=total - wallet_amount_used,
                is_paid=is_paid,
                status='CONFIRMED',
                payment_status='COMPLETED' if is_paid else 'PENDING',
                **validated_data
            )

            # Link/Create the wallet transaction record directly with the order
            if wallet_to_deduct > 0 and wallet_obj:
                from apps.wallet.models import WalletTransaction
                WalletTransaction.objects.create(
                    wallet=wallet_obj,
                    amount=-wallet_to_deduct,
                    reason='ORDER_PAYMENT',
                    balance_before=deducted_balance_before,
                    balance_after=deducted_balance_after,
                    related_order=order,
                    notes=f"Wallet split payment for order {order.tracking_id}"
                )

            # 6. Create items, deduct stock, and calculate organic impact
            order_water = Decimal('0.00')
            order_soil = Decimal('0.00')
            order_chemical = Decimal('0.00')
            order_farmer = Decimal('0.00')

            for item in order_items_to_create:
                batch = item.pop('batch')
                qty = item['quantity']
                
                batch.stock_level -= qty
                batch.save()
                
                # Dynamic organic impact calculation
                product = batch.variant.product
                order_water += product.water_score * qty
                order_soil += product.soil_score * qty
                order_chemical += product.chemical_score * qty
                order_farmer += product.farmer_score * qty
                
                OrderItem.objects.create(order=order, batch=batch, **item)

            # Update the order with calculated impact scores
            order.order_water = order_water
            order.order_soil = order_soil
            order.order_chemical = order_chemical
            order.order_farmer = order_farmer
            order.save(update_fields=['order_water', 'order_soil', 'order_chemical', 'order_farmer'])

            # Update or create customer lifetime impact record
            from apps.wallet.models import CustomerImpact
            impact, _ = CustomerImpact.objects.get_or_create(user=user)
            impact.total_water += order_water
            impact.total_soil += order_soil
            impact.total_chemical += order_chemical
            impact.total_farmer += order_farmer
            impact.total_orders += 1
            impact.save()

            return order

class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    organic_impact = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

    def get_organic_impact(self, obj):
        user = self.context['request'].user if 'request' in self.context else obj.user
        return get_organic_impact_data(obj, user)

    def get_items(self, obj):
        from apps.inventory.serializers import InventoryBatchSerializer
        items = obj.items.all()
        return [
            {
                "id": i.id,
                "batch": InventoryBatchSerializer(i.batch).data if i.batch else None,
                "product_name": i.product_name,
                "price": float(i.price),
                "quantity": i.quantity,
                "unit": i.unit,
                "total": float(i.price * i.quantity)
            } for i in items
        ]
