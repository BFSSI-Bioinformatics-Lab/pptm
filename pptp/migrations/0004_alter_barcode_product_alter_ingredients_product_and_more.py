# Generated by Django 5.0.9 on 2024-10-30 16:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pptp", "0003_barcode_device_filename_barcode_is_uploaded_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="barcode",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)ss",
                to="pptp.product",
            ),
        ),
        migrations.AlterField(
            model_name="ingredients",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)ss",
                to="pptp.product",
            ),
        ),
        migrations.AlterField(
            model_name="nutritionfacts",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)ss",
                to="pptp.product",
            ),
        ),
        migrations.AlterField(
            model_name="productimage",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)ss",
                to="pptp.product",
            ),
        ),
    ]