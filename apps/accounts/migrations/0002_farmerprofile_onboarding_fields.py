from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField("farmerprofile", "farm_name", models.CharField(blank=True, max_length=255)),
        migrations.AddField("farmerprofile", "latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField("farmerprofile", "longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField("farmerprofile", "total_acreage", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
        migrations.AddField("farmerprofile", "crops", models.JSONField(blank=True, default=list)),
        migrations.AddField("farmerprofile", "organic_pledge_accepted", models.BooleanField(default=False)),
        migrations.AddField("farmerprofile", "organic_pledge_signature", models.CharField(blank=True, max_length=255)),
        migrations.AddField("farmerprofile", "organic_pledge_accepted_at", models.DateTimeField(blank=True, null=True)),
    ]
