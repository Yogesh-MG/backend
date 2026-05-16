# Generated manually

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("farmer", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmernotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("new_order", "New Order"),
                    ("payment_credited", "Payment Credited"),
                    ("quality_alert", "Quality Alert"),
                    ("pickup_scheduled", "Pickup Scheduled"),
                    ("general", "General"),
                ],
                default="general",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="farmernotification",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
