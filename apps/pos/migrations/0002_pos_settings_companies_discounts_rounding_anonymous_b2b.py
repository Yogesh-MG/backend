# Generated manually — POS Feature Enhancement: Settings, Discounts, Rounding, Privacy, B2B

import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0001_initial"),
    ]

    operations = [
        # ── PosEmployee additions ──
        migrations.AddField(
            model_name="posemployee",
            name="is_manager",
            field=models.BooleanField(
                default=False, help_text="Can authorize refunds and returns"
            ),
        ),

        # ── PosShift additions ──
        migrations.AddField(
            model_name="posshift",
            name="rounding_loss",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10,
                help_text="Total rounding adjustment loss for this shift"
            ),
        ),

        # ── New models ──
        migrations.CreateModel(
            name="PosSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "pride_discount_pct",
                    models.DecimalField(
                        decimal_places=4, default=Decimal("0.3000"), max_digits=5,
                        help_text="PRIDE member discount rate (e.g. 0.30 = 30%)"
                    ),
                ),
                (
                    "rounding_enabled",
                    models.BooleanField(default=True, help_text="Enable cash rounding"),
                ),
                (
                    "rounding_slab",
                    models.PositiveIntegerField(
                        default=5, choices=[(5, "₹5"), (10, "₹10")],
                        help_text="Round change up to nearest denomination"
                    ),
                ),
                (
                    "max_manual_discount_pct",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("5.00"), max_digits=5,
                        help_text="Maximum manual discount % without manager override"
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "POS Settings",
                "verbose_name_plural": "POS Settings",
            },
        ),
        migrations.CreateModel(
            name="CompanyProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "gstin",
                    models.CharField(max_length=15, unique=True, help_text="15-character GSTIN"),
                ),
                ("address", models.TextField(blank=True)),
                (
                    "pan",
                    models.CharField(max_length=10, blank=True, help_text="10-character PAN"),
                ),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Company Profile",
                "verbose_name_plural": "Company Profiles",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PosInvoiceCounter",
            fields=[
                ("year", models.PositiveIntegerField(primary_key=True, serialize=False)),
                ("last_number", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "POS Invoice Counter",
                "verbose_name_plural": "POS Invoice Counters",
            },
        ),

        # ── PosTransaction additions ──
        migrations.AddField(
            model_name="postransaction",
            name="transaction_type",
            field=models.CharField(
                choices=[("SALE", "Sale"), ("RETURN", "Return")],
                default="SALE",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="related_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="returns",
                to="pos.postransaction",
                help_text="For RETURN type: links to the original SALE transaction",
            ),
        ),
        migrations.AlterField(
            model_name="postransaction",
            name="method",
            field=models.CharField(
                choices=[
                    ("Cash", "Cash"),
                    ("UPI", "UPI"),
                    ("Card", "Card"),
                    ("Sodexo", "Sodexo"),
                    ("Wallet", "Wallet"),
                    ("Split", "Split Payment"),
                ],
                default="Cash",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="manual_discount_percentage",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=5,
                help_text="Manual discount % applied"
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="manual_discount_amount",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10,
                help_text="Manual discount amount in ₹"
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="discount_reason",
            field=models.TextField(blank=True, help_text="Reason for manual discount"),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="discount_applied_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="discounted_transactions",
                to="pos.posemployee",
                help_text="Employee who authorized the manual discount",
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="rounding_adjustment",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10,
                help_text="Rounding amount added to total (positive = round up)"
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="is_anonymous",
            field=models.BooleanField(
                default=False, help_text="Transaction without customer identification"
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="is_b2b",
            field=models.BooleanField(
                default=False, help_text="B2B / company purchase with GST invoice"
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="pos.companyprofile",
            ),
        ),
        migrations.AddField(
            model_name="postransaction",
            name="invoice_number",
            field=models.CharField(
                blank=True, db_index=True, max_length=30, help_text="Sequential tax invoice ID"
            ),
        ),

        # ── PosTransactionItem additions ──
        migrations.AddField(
            model_name="postransactionitem",
            name="gst_rate",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("18.00"), max_digits=5,
                help_text="GST % at time of sale"
            ),
        ),

        # ── PosTender method choices update ──
        migrations.AlterField(
            model_name="postender",
            name="method",
            field=models.CharField(
                choices=[
                    ("Cash", "Cash"),
                    ("UPI", "UPI"),
                    ("Card", "Card"),
                    ("Sodexo", "Sodexo"),
                    ("Wallet", "Wallet"),
                    ("Split", "Split Payment"),
                ],
                max_length=20,
            ),
        ),
    ]
