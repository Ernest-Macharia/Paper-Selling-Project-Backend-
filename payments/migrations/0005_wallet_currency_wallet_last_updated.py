# Generated by Django 5.1.7 on 2025-07-15 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_wallet_last_withdrawal_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallet",
            name="currency",
            field=models.CharField(
                choices=[
                    ("USD", "US Dollar"),
                    ("EUR", "Euro"),
                    ("KES", "Kenyan Shilling"),
                    ("GBP", "British Pound"),
                ],
                default="USD",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="wallet",
            name="last_updated",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
