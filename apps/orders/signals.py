"""
Signals for the orders app.

Sends push notifications to farmers when their products are ordered.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='orders.Order')
def notify_farmers_on_new_order(sender, instance, created, **kwargs):
    """
    Send push notifications to farmers when a new order is placed
    containing their products.
    """
    if not created:
        return
    
    try:
        from apps.farmer.notifications import notify_new_order
        from apps.accounts.models import FarmerProfile
        
        # Get all farmer profiles for items in this order
        farmer_ids = set()
        for item in instance.items.all():
            if item.batch and item.batch.farmer_id:
                farmer_ids.add(item.batch.farmer_id)
        
        # Send notification to each farmer
        for farmer_id in farmer_ids:
            try:
                farmer = FarmerProfile.objects.get(id=farmer_id)
                # Get the first item for this farmer for the notification
                farmer_item = next(
                    (item for item in instance.items.all() 
                     if item.batch and item.batch.farmer_id == farmer_id),
                    None
                )
                if farmer_item:
                    notify_new_order(
                        farmer,
                        instance.tracking_id or str(instance.id),
                        farmer_item.product_name,
                        f"{farmer_item.quantity} {farmer_item.unit}"
                    )
            except FarmerProfile.DoesNotExist:
                logger.warning(f"FarmerProfile {farmer_id} not found for order notification")
            except Exception as e:
                logger.error(f"Failed to send notification to farmer {farmer_id}: {e}")
                
    except ImportError:
        logger.debug("Farmer notifications not available")
    except Exception as e:
        logger.error(f"Error in notify_farmers_on_new_order signal: {e}")
