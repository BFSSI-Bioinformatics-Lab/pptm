from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Product(models.Model):
    """
    Main product model to store product information and metadata
    """
    # Existing fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_products'
    )
    submission_complete = models.BooleanField(default=False)
    
    product_name = models.CharField(
        max_length=255,
        help_text=_("Full product name as shown on packaging")
    )
    is_variety_pack = models.BooleanField(
        default=False,
        help_text=_("Check if this is a variety/multi-pack product")
    )
    has_multiple_nutrition_facts = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple nutrition facts tables")
    )
    has_multiple_barcodes = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple barcodes")
    )
    
    def __str__(self):
        return f"{self.product_name} (Product {self.id})"


class Barcode(models.Model):
    """
    Store multiple barcodes for a single product
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='barcodes'
    )
    barcode_image = models.ImageField(
        upload_to='barcodes/',
        help_text=_("Image of the product barcode")
    )
    barcode_number = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Barcode number if automatically detected")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Barcode {self.barcode_number} for Product {self.product.id}"


class NutritionFacts(models.Model):
    """
    Store nutrition facts table images and related data
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='nutrition_facts'
    )
    image = models.ImageField(
        upload_to='nutrition_facts/',
        help_text=_("Image of the nutrition facts table")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Any additional notes about this nutrition facts table")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Nutrition Facts"

    def __str__(self):
        return f"Nutrition Facts for Product {self.product.id}"


class Ingredients(models.Model):
    """
    Store ingredients list images
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ingredients'
    )
    image = models.ImageField(
        upload_to='ingredients/',
        help_text=_("Image of the ingredients list")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Any additional notes about the ingredients list")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Ingredients"

    def __str__(self):
        return f"Ingredients for Product {self.product.id}"


class ProductImage(models.Model):
    """
    Store additional product images (front, sides, etc.)
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_images'
    )
    image = models.ImageField(
        upload_to='product_images/',
        help_text=_("Product image")
    )
    image_type = models.CharField(
        max_length=50,
        choices=[
            ('front', _('Front')),
            ('back', _('Back')),
            ('side', _('Side')),
            ('other', _('Other')),
        ],
        help_text=_("Type of product image")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Any additional notes about this image")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_image_type_display()} image for Product {self.product.id}"