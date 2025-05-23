# Generated by Django 5.0.9 on 2024-11-01 15:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pptp", "0004_alter_barcode_product_alter_ingredients_product_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="barcode",
            name="barcode_image_or_device_filename_required",
        ),
        migrations.RemoveField(
            model_name="barcode",
            name="barcode_image",
        ),
        migrations.AddField(
            model_name="barcode",
            name="image",
            field=models.ImageField(
                blank=True, help_text="Image file", null=True, upload_to="images/"
            ),
        ),
        migrations.AlterField(
            model_name="barcode",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s",
                to="pptp.product",
            ),
        ),
        migrations.AlterField(
            model_name="ingredients",
            name="image",
            field=models.ImageField(
                blank=True, help_text="Image file", null=True, upload_to="images/"
            ),
        ),
        migrations.AlterField(
            model_name="ingredients",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s",
                to="pptp.product",
            ),
        ),
        migrations.AlterField(
            model_name="nutritionfacts",
            name="image",
            field=models.ImageField(
                blank=True, help_text="Image file", null=True, upload_to="images/"
            ),
        ),
        migrations.AlterField(
            model_name="nutritionfacts",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s",
                to="pptp.product",
            ),
        ),
        migrations.AlterField(
            model_name="productimage",
            name="image",
            field=models.ImageField(
                blank=True, help_text="Image file", null=True, upload_to="images/"
            ),
        ),
        migrations.AlterField(
            model_name="productimage",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s",
                to="pptp.product",
            ),
        ),
        migrations.AddConstraint(
            model_name="barcode",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("image__isnull", False), ("is_uploaded", True)),
                    models.Q(
                        ("device_filename__isnull", False), ("is_uploaded", False)
                    ),
                    _connector="OR",
                ),
                name="barcode_image_or_device_filename_required",
            ),
        ),
    ]
