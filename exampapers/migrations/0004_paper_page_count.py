# Generated by Django 5.1.7 on 2025-05-29 22:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exampapers", "0003_school_paper_school"),
    ]

    operations = [
        migrations.AddField(
            model_name="paper",
            name="page_count",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
