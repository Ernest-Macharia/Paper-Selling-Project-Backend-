# Generated by Django 5.1.7 on 2025-07-22 15:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exampapers", "0014_paper_year"),
    ]

    operations = [
        migrations.AddField(
            model_name="paper",
            name="preview_image",
            field=models.ImageField(blank=True, null=True, upload_to="preview_images/"),
        ),
    ]
