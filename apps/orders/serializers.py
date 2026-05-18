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
            'id', 'tracking_id', 'address_title', 'address_line', 'delivery_slot', 
            'payment_method', 'items', 'subtotal', 'delivery_fee', 'total', 'is_paid'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # Remove fields that might be passed twice (from perform_create or frontend)
        validated_data.pop('subtotal', None)
        validated_data.pop('delivery_fee', None)
        validated_data.pop('total', None)
        validated_data.pop('is_paid', None)
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

                item_price = batch.price
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
            wallet_amount_used = Decimal('0.00')
            is_paid = False

            if payment_method == 'WALLET':
                from apps.wallet.models import WalletTransaction
                try:
                    wallet = Wallet.objects.get(user=user)
                    if wallet.balance < total:
                        raise serializers.ValidationError(f"Insufficient wallet balance. Required: ₹{total}, Available: ₹{wallet.balance}")
                    
                    # Record balance before deduction
                    balance_before = wallet.balance
                    wallet.balance -= total
                    wallet.save(update_fields=['balance'])
                    
                    wallet_amount_used = total
                    is_paid = True
                    
                    # Create the transaction record for the ledger
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=-total,
                        reason='ORDER_PAYMENT',
                        balance_before=balance_before,
                        balance_after=wallet.balance,
                        notes=f"Initial payment for order creation"
                    )
                except Wallet.DoesNotExist:
                    raise serializers.ValidationError("No wallet found for this user. Please top up first.")

            # 5. Create the Order with calculated values
            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=total,
                member_discount=member_discount,
                pride_limit_used=pride_limit_used,
                wallet_amount_used=wallet_amount_used,
                is_paid=is_paid,
                status='CONFIRMED',
                payment_status='COMPLETED' if is_paid else 'PENDING',
                **validated_data
            )

            # Link the wallet transaction to the order if it was created
            if payment_method == 'WALLET':
                txn = WalletTransaction.objects.filter(wallet__user=user, reason='ORDER_PAYMENT', related_order__isnull=True).order_by('-created_at').first()
                if txn:
                    txn.related_order = order
                    txn.save(update_fields=['related_order'])

            # 6. Create items and deduct stock
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
