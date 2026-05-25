"""
Order modification service — handles adding/removing items from orders
with automatic wallet refund/transaction logic.
"""
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone
from .models import Order, OrderItem
from apps.inventory.models import InventoryBatch
from apps.wallet.models import Wallet, WalletTransaction
from apps.picker.models import PickerTask


class OrderModificationService:
    """Service for modifying orders until picker task is packed."""
    
    # Order can be modified if picker task is in these statuses
    MODIFIABLE_STATUSES = ['QUEUED', 'IN_PROGRESS']
    
    @staticmethod
    def can_modify_order(order: Order) -> tuple[bool, str]:
        """Check if order can be modified. Returns (can_modify, reason)."""
        try:
            picker_task = PickerTask.objects.get(order=order)
            
            if picker_task.status in ['PACKED', 'HANDED_OVER', 'CANCELLED']:
                return False, f"Cannot modify order once it's {picker_task.status.lower()}"
            
            return True, "Order can be modified"
        except PickerTask.DoesNotExist:
            # If no picker task yet, order can still be modified
            return True, "Order can be modified"
    
    @staticmethod
    @db_transaction.atomic
    def add_item_to_order(order: Order, batch_id: int, quantity: int) -> dict:
        """Add a product item to an existing order with wallet transaction if needed."""
        
        can_modify, reason = OrderModificationService.can_modify_order(order)
        if not can_modify:
            raise ValueError(reason)
        
        # Fetch batch
        try:
            batch = InventoryBatch.objects.get(id=batch_id)
        except InventoryBatch.DoesNotExist:
            raise ValueError(f"Product batch {batch_id} not found")
        
        # Check stock
        if batch.stock_level < quantity:
            raise ValueError(f"Insufficient stock. Available: {batch.stock_level}")
        
        # Create or increment order item
        item_total = batch.variant.price * Decimal(quantity)
        
        order_item, created = OrderItem.objects.get_or_create(
            order=order,
            batch=batch,
            defaults={
                'product_name': batch.variant.product.name or "Fresh Produce",
                'price': batch.variant.price,
                'quantity': quantity,
                'unit': batch.variant.unit or "kg"
            }
        )
        
        if not created:
            order_item.quantity += quantity
            order_item.save(update_fields=['quantity'])
        
        # Update order totals
        old_subtotal = order.subtotal
        order.subtotal = old_subtotal + item_total
        order.total = order.subtotal + order.delivery_fee
        order.save(update_fields=['subtotal', 'total', 'updated_at'])
        
        # Create wallet transaction if wallet was used in payment
        wallet_transaction = None
        if order.wallet_amount_used > 0 and order.payment_status == 'COMPLETED':
            wallet_transaction = OrderModificationService._create_wallet_transaction(
                order=order,
                amount=item_total,
                reason='PRODUCT_ADDITION',
                notes=f"Product added to order {order.tracking_id}: {order_item.product_name}"
            )
            # Sync wallet_amount_used on the order
            order.wallet_amount_used += item_total
            order.save(update_fields=['wallet_amount_used', 'updated_at'])
        
        # Determine if additional payment is required
        additional_payment_required = False
        additional_payment_amount = Decimal('0')
        
        # If order was paid via non-wallet method and new total exceeds original paid amount
        if order.payment_status == 'COMPLETED' and order.wallet_amount_used == 0:
            # Calculate the original paid amount (before adding this item)
            original_paid = order.total - item_total
            if order.total > original_paid:
                additional_payment_required = True
                additional_payment_amount = item_total
        
        # If wallet was used but doesn't have enough balance for the addition
        if wallet_transaction and order.wallet_amount_used > 0:
            try:
                wallet = Wallet.objects.get(user=order.user)
                if wallet.balance < 0:
                    additional_payment_required = True
                    additional_payment_amount = abs(wallet.balance)
            except Wallet.DoesNotExist:
                pass
        
        return {
            "order_item_id": order_item.id,
            "product_name": order_item.product_name,
            "quantity": quantity,
            "price": float(batch.variant.price),
            "total": float(item_total),
            "new_order_total": float(order.total),
            "wallet_transaction": {
                "id": wallet_transaction.id if wallet_transaction else None,
                "amount": float(item_total) if wallet_transaction else 0,
            } if wallet_transaction else None,
            "payment": {
                "additional_payment_required": additional_payment_required,
                "additional_payment_amount": float(additional_payment_amount),
                "order_total": float(order.total),
                "payment_status": order.payment_status,
            }
        }
    
    @staticmethod
    @db_transaction.atomic
    def remove_item_from_order(order: Order, order_item_id: int) -> dict:
        """Remove an item from order and refund wallet if payment was made.
        Auto-cancels order if no items remain."""
        
        can_modify, reason = OrderModificationService.can_modify_order(order)
        if not can_modify:
            raise ValueError(reason)
        
        try:
            order_item = OrderItem.objects.get(id=order_item_id, order=order)
        except OrderItem.DoesNotExist:
            raise ValueError(f"Order item {order_item_id} not found in this order")
        
        item_total = Decimal(order_item.price * order_item.quantity)
        
        # Update order totals
        order.subtotal = order.subtotal - item_total
        order.total = max(Decimal('0'), order.subtotal + order.delivery_fee)
        order.save(update_fields=['subtotal', 'total', 'updated_at'])
        
        # Create wallet refund transaction if wallet was used
        wallet_transaction = None
        if order.wallet_amount_used > 0 and order.payment_status == 'COMPLETED':
            wallet_transaction = OrderModificationService._refund_to_wallet(
                order=order,
                amount=item_total,
                reason='PRODUCT_REMOVAL',
                notes=f"Refund for removed product from order {order.tracking_id}: {order_item.product_name}"
            )
            # Sync wallet_amount_used on the order
            order.wallet_amount_used = max(Decimal('0'), order.wallet_amount_used - item_total)
            order.save(update_fields=['wallet_amount_used', 'updated_at'])
        
        # Delete the item
        order_item.delete()
        
        # Check if order has no items left - auto cancel
        remaining_items = OrderItem.objects.filter(order=order).count()
        auto_cancelled = False
        if remaining_items == 0:
            auto_cancelled = True
            OrderModificationService._cancel_order(order, "User removed all items")
        
        return {
            "removed_item": {
                "product_name": order_item.product_name,
                "quantity": order_item.quantity,
                "price": float(order_item.price),
                "total": float(item_total)
            },
            "new_order_total": float(order.total),
            "wallet_refund": {
                "id": wallet_transaction.id if wallet_transaction else None,
                "amount": float(item_total) if wallet_transaction else 0,
            } if wallet_transaction else None,
            "auto_cancelled": auto_cancelled,
            "message": "Order cancelled - all items removed" if auto_cancelled else None
        }

    @staticmethod
    @db_transaction.atomic
    def update_item_quantity(order: Order, order_item_id: int, quantity: int) -> dict:
        """Update an item quantity and handle price difference via wallet."""
        
        can_modify, reason = OrderModificationService.can_modify_order(order)
        if not can_modify:
            raise ValueError(reason)
            
        if quantity <= 0:
            return OrderModificationService.remove_item_from_order(order, order_item_id)
            
        try:
            order_item = OrderItem.objects.get(id=order_item_id, order=order)
        except OrderItem.DoesNotExist:
            raise ValueError(f"Order item {order_item_id} not found in this order")
            
        old_quantity = order_item.quantity
        diff = quantity - old_quantity
        
        if diff == 0:
            return {"message": "No change in quantity"}
            
        # Check stock for increases
        if diff > 0:
            if order_item.batch.stock_level < diff:
                raise ValueError(f"Insufficient stock. Available: {order_item.batch.stock_level}")
        
        diff_total = order_item.price * Decimal(diff)
        
        # Update item and stock
        order_item.quantity = quantity
        order_item.save(update_fields=['quantity'])
        
        # Adjust stock level in inventory
        if order_item.batch:
            order_item.batch.stock_level -= diff
            order_item.batch.save(update_fields=['stock_level', 'updated_at'])
        
        # Update order totals
        order.subtotal = order.subtotal + diff_total
        order.total = max(Decimal('0'), order.subtotal + order.delivery_fee)
        order.save(update_fields=['subtotal', 'total', 'updated_at'])
        
        # Handle wallet transaction/refund if payment was made
        wallet_transaction = None
        if order.wallet_amount_used > 0 and order.payment_status == 'COMPLETED':
            if diff > 0:
                # Debit
                wallet_transaction = OrderModificationService._create_wallet_transaction(
                    order=order,
                    amount=diff_total,
                    reason='PRODUCT_UPDATE',
                    notes=f"Quantity increased for {order_item.product_name} in order {order.tracking_id}"
                )
                # Sync wallet_amount_used on the order
                order.wallet_amount_used += diff_total
                order.save(update_fields=['wallet_amount_used', 'updated_at'])
            else:
                # Refund
                wallet_transaction = OrderModificationService._refund_to_wallet(
                    order=order,
                    amount=abs(diff_total),
                    reason='PRODUCT_UPDATE',
                    notes=f"Quantity decreased for {order_item.product_name} in order {order.tracking_id}"
                )
                # Sync wallet_amount_used on the order
                order.wallet_amount_used = max(Decimal('0'), order.wallet_amount_used - abs(diff_total))
                order.save(update_fields=['wallet_amount_used', 'updated_at'])
                
        # Determine if additional payment is required for quantity increase
        additional_payment_required = False
        additional_payment_amount = Decimal('0')
        if diff > 0 and order.payment_status == 'COMPLETED':
            # Check total paid amount
            total_paid = order.wallet_amount_used
            try:
                from apps.payment.models import PaymentTransaction
                pt = PaymentTransaction.objects.filter(order=order, status='COMPLETED').first()
                if pt:
                    total_paid += pt.amount
            except Exception:
                pass
            due = order.total - total_paid
            if due > Decimal('0.05'):
                additional_payment_required = True
                additional_payment_amount = due

        return {
            "order_item_id": order_item.id,
            "product_name": order_item.product_name,
            "old_quantity": old_quantity,
            "new_quantity": quantity,
            "price": float(order_item.price),
            "diff_total": float(diff_total),
            "new_order_total": float(order.total),
            "wallet_adjustment": {
                "id": wallet_transaction.id if wallet_transaction else None,
                "amount": float(abs(diff_total)) if wallet_transaction else 0,
                "type": "REFUND" if diff < 0 else "DEBIT"
            } if wallet_transaction else None,
            "payment": {
                "additional_payment_required": additional_payment_required,
                "additional_payment_amount": float(additional_payment_amount),
                "order_total": float(order.total),
                "payment_status": order.payment_status,
            }
        }
    
    @staticmethod
    def _create_wallet_transaction(order: Order, amount: Decimal, reason: str, notes: str) -> WalletTransaction:
        """Create a wallet debit transaction when product is added."""
        try:
            wallet = Wallet.objects.get(user=order.user)
        except Wallet.DoesNotExist:
            # Create wallet if not exists
            wallet = Wallet.objects.create(user=order.user)
        
        # Debit from wallet
        balance_before = wallet.balance
        wallet.balance = max(Decimal('0'), wallet.balance - amount)
        wallet.save(update_fields=['balance', 'updated_at'])
        
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            amount=-amount,  # Negative = debit
            reason=reason,
            balance_before=balance_before,
            balance_after=wallet.balance,
            related_order=order,
            notes=notes
        )
        
        return transaction
    
    @staticmethod
    @db_transaction.atomic
    def cancel_order(order: Order, reason: str = "User cancelled") -> dict:
        """Cancel an order and refund wallet if payment was made."""
        
        can_modify, mod_reason = OrderModificationService.can_modify_order(order)
        if not can_modify:
            raise ValueError(f"Cannot cancel order: {mod_reason}")
        
        # Refund full wallet amount if payment was completed
        wallet_refund = None
        if order.wallet_amount_used > 0 and order.payment_status == 'COMPLETED':
            wallet_refund = OrderModificationService._refund_to_wallet(
                order=order,
                amount=order.wallet_amount_used,
                reason='ORDER_CANCELLATION',
                notes=f"Full refund for cancelled order {order.tracking_id}: {reason}"
            )
        
        # Cancel the order
        OrderModificationService._cancel_order(order, reason)
        
        return {
            "cancelled": True,
            "tracking_id": order.tracking_id,
            "reason": reason,
            "wallet_refund": {
                "id": wallet_refund.id if wallet_refund else None,
                "amount": float(order.wallet_amount_used) if wallet_refund else 0,
            } if wallet_refund else None
        }
    
    @staticmethod
    def _cancel_order(order: Order, reason: str):
        """Internal method to mark order as cancelled."""
        from apps.picker.models import PickerTask
        
        order.status = 'CANCELLED'
        order.save(update_fields=['status', 'updated_at'])
        
        # Also cancel any associated picker task
        try:
            picker_task = PickerTask.objects.get(order=order)
            picker_task.status = 'CANCELLED'
            picker_task.save(update_fields=['status', 'updated_at'])
        except PickerTask.DoesNotExist:
            pass
    
    @staticmethod
    def _refund_to_wallet(order: Order, amount: Decimal, reason: str, notes: str) -> WalletTransaction:
        """Create a wallet credit transaction (refund) when product is removed."""
        try:
            wallet = Wallet.objects.get(user=order.user)
        except Wallet.DoesNotExist:
            wallet = Wallet.objects.create(user=order.user)
        
        # Credit to wallet
        balance_before = wallet.balance
        wallet.balance = wallet.balance + amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,  # Positive = credit
            reason=reason,
            balance_before=balance_before,
            balance_after=wallet.balance,
            related_order=order,
            notes=notes
        )
        
        return transaction
