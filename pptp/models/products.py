from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Product(models.Model):
    """
    Main product model to store product information and metadata
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Username from request headers")
    )
    submission_complete = models.BooleanField(default=False)

    is_offline = models.BooleanField(
        default=False,
        help_text=_("Whether this product was created in offline mode")
    )
    offline_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Unique identifier for offline submissions")
    )
    
    product_name = models.CharField(
        max_length=255,
        help_text=_("Full product name as shown on packaging")
    )

    is_variety_pack = models.BooleanField(
        default=False,
        help_text=_("Check if this is a variety/multi-pack product")
    )
    is_supplemented_food = models.BooleanField(
        default=False,
        help_text=_("Check if this is a Supplemented Food as indicated by the front-of-pack caution identifier and supplemented food facts table")
    )
    has_front_of_pack_label = models.BooleanField(
        default=False,
        help_text=_("Check if this has a front of pack nutrition symbol")
    )
    has_multiple_nutrition_facts = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple nutrition facts tables")
    )
    has_multiple_barcodes = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple barcodes")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['created_by', 'offline_id'],
                name='unique_offline_id_per_user',
                condition=models.Q(is_offline=True)
            )
        ]
    
    def __str__(self):
        return f"{self.product_name} (Product {self.id})"


class BaseImageModel(models.Model):
    """
    Abstract base class for all image-related models
    """
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True,
        help_text=_("Any additional notes")
    )
    image = models.ImageField(
        upload_to='images/',  # Will be overridden in child classes
        help_text=_("Image file"),
        null=True,
        blank=True
    )
    
    # Offline mode fields
    device_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Original filename from device camera")
    )
    is_uploaded = models.BooleanField(
        default=True,
        help_text=_("Whether the image has been uploaded to the server")
    )

    class Meta:
        abstract = True


class Barcode(BaseImageModel):
    """Store barcode images"""
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='barcodes'
    )
    barcode_number = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Barcode number if automatically detected")
    )
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(image__isnull=False, is_uploaded=True) |
                    models.Q(device_filename__isnull=False, is_uploaded=False)
                ),
                name='barcode_image_or_device_filename_required'
            )
        ]


class NutritionFacts(BaseImageModel):
    """Store nutrition facts table images"""
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='nutrition_facts'
    )
    
    class Meta:
        verbose_name_plural = "Nutrition Facts"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(image__isnull=False, is_uploaded=True) |
                    models.Q(device_filename__isnull=False, is_uploaded=False)
                ),
                name='nutrition_image_or_device_filename_required'
            )
        ]


class Ingredients(BaseImageModel):
    """Store ingredients list images"""
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='ingredients'
    )
    
    class Meta:
        verbose_name_plural = "Ingredients"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(image__isnull=False, is_uploaded=True) |
                    models.Q(device_filename__isnull=False, is_uploaded=False)
                ),
                name='ingredients_image_or_device_filename_required'
            )
        ]


class ProductImage(BaseImageModel):
    """Store additional product images (front, sides, etc.)"""
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='product_images'
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(image__isnull=False, is_uploaded=True) |
                    models.Q(device_filename__isnull=False, is_uploaded=False)
                ),
                name='product_image_or_device_filename_required'
            )
        ]
