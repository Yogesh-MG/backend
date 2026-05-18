"""
Management command: credit_monthly_pride

Run on the 1st of every month (via cron or celery beat):
  python manage.py credit_monthly_pride

Adds the tier-based monthly PRIDE discount limit to each PRIDE member's wallet.
Does NOT reset the limit — it accumulates carry-forward.
Also credits the monthly wallet balance credit (10% of invested amount).
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
                # ── 1. Credit PRIDE discount limit ──
                tier_limits = {
                    'TIER_1': Decimal('3000.00'),
                    'TIER_2': Decimal('6000.00'),
                    'TIER_3': Decimal('10000.00'),
                }
                monthly_limit = tier_limits.get(partnership.tier, Decimal('0.00'))
                if monthly_limit > 0:
                    wallet.accumulated_pride_limit += monthly_limit
                    limit_count += 1

                # ── 2. Credit wallet balance (monthly percentage) ──
                monthly_credit = (partnership.invested_amount * partnership.monthly_credit_percentage) / Decimal('100.00')
                if monthly_credit > 0:
                    balance_before = wallet.balance
                    wallet.balance += monthly_credit
                    wallet_count += 1

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=monthly_credit,
                        reason='MONTHLY_CREDIT',
                        balance_before=balance_before,
                        balance_after=wallet.balance,
                        notes=f"Monthly credit ({partnership.monthly_credit_percentage}%) for {partnership.tier}"
                    )

                wallet.last_monthly_credit_date = now
                wallet.save(update_fields=['accumulated_pride_limit', 'balance', 'last_monthly_credit_date'])

        self.stdout.write(self.style.SUCCESS(
            f"Credited {limit_count} PRIDE limits and {wallet_count} wallet balances for {now.strftime('%B %Y')}"
        ))
