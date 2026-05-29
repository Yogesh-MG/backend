"""
Management command: credit_monthly_pride

Run on the 1st of every month (via cron or celery beat):
  python manage.py credit_monthly_pride

Adds the tier-based monthly PRIDE discount limit to each PRIDE member's wallet.
Does NOT reset the limit — it accumulates carry-forward.

Note: Monthly wallet credit (10% of purchase) is now credited at order time,
not monthly. This ensures users only get credit for actual purchases within
their tier limit.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.wallet.models import Wallet, WalletTransaction, Partnership


class Command(BaseCommand):
    help = "Credit monthly PRIDE limit and wallet balance to all PRIDE members"

    def handle(self, *args, **options):
        now = timezone.now()
        partnerships = Partnership.objects.filter(refund_requested=False)
        limit_count = 0
        wallet_count = 0

        for partnership in partnerships:
            try:
                wallet = Wallet.objects.get(user=partnership.user)
            except Wallet.DoesNotExist:
                continue

            # Skip if already credited this month
            if wallet.last_monthly_credit_date and wallet.last_monthly_credit_date.month == now.month and wallet.last_monthly_credit_date.year == now.year:
                continue

            with transaction.atomic():
                # ── Credit PRIDE discount limit ──
                # This limit is used for BOTH discount eligibility AND wallet credit eligibility
                tier_limits = {
                    'TIER_1': Decimal('3000.00'),
                    'TIER_2': Decimal('6000.00'),
                    'TIER_3': Decimal('10000.00'),
                }
                monthly_limit = tier_limits.get(partnership.tier, Decimal('0.00'))
                if monthly_limit > 0:
                    wallet.accumulated_pride_limit += monthly_limit
                    limit_count += 1

                # Note: Monthly wallet credit (10% of purchase) is now credited at order time
                # in the order serializer, not here. This ensures users only get credit for
                # actual purchases within their tier limit.

                wallet.last_monthly_credit_date = now
                wallet.save(update_fields=['accumulated_pride_limit', 'last_monthly_credit_date'])

        self.stdout.write(self.style.SUCCESS(
            f"Credited {limit_count} PRIDE limits for {now.strftime('%B %Y')}. "
            f"Wallet credits (10% of purchase) are applied at order time."
        ))
