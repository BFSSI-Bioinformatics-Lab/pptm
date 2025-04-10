# Generated by Django 5.0.9 on 2024-11-14 19:27

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pptp", "0007_alter_barcode_product_alter_ingredients_product_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="has_front_of_pack_label",
            field=models.BooleanField(
                default=False,
                help_text="Check if this has a front of pack nutrition symbol",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="is_supplemented_food",
            field=models.BooleanField(
                default=False,
                help_text="Check if this is a Supplemented Food as indicated by the front-of-pack caution identifier and supplemented food facts table",
            ),
        ),
    ]
