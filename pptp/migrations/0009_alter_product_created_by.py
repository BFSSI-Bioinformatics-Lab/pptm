# Generated by Django 4.2.3 on 2025-02-03 19:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pptp", "0008_product_has_front_of_pack_label_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="created_by",
            field=models.CharField(
                blank=True,
                help_text="Username from request headers",
                max_length=255,
                null=True,
            ),
        ),
    ]
