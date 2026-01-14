from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from ..storage.azure import AzureBlobStorage, AzureBlobStorageError


User = get_user_model()

UNIT_CHOICES = [
    ("MG", "Milligrams"),
    ("G", "Grams"),
    ("KG", "Kilograms"),
    ("ML", "Millilitres"),
    ("L", "Litres"),
    ("OTH", "Other"),
]

STORAGE_CHOICES = [
    ("shelf_stable", "Shelf Stable"),
    ("fridge", "Fridge"),
    ("freezer", "Freezer"),
]

PACKAGING_CHOICES = [
    ("glass", "Glass"),
    ("metal", "Metal"),
    ("paper", "Paper/paperboard"),
    ("plastic_pet", "Plastic - PET - 1"),
    ("plastic_hdpe", "Plastic - HDPE - 2"),
    ("plastic_pvc", "Plastic - PVC - 3"),
    ("plastic_ldpe", "Plastic - LDPE - 4"),
    ("plastic_pp", "Plastic - PP - 5"),
    ("plastic_ps", "Plastic - PS - 6"),
    ("plastic_other", "Plastic - OTHER - 7"),
    ("plastic_unknown", "Plastic - Unknown"),
    ("other", "Other"),
]

BATCH_CHOICES = [
    ("2025_snapcan","SNAP-CAN 2025"),
    ("2026_baked_goods","2026 Baked Goods Collection"),
    ("2026_snack_foods","2026 Snack Foods Collection"),
    ("tds","Total Diet Study"),
    ("2025_supp_food","2025 Supplemented Food Collection"),
    ("2025_frozen_entrees","2025 Frozen Entrees Collection"),
]


def get_upload_path(instance, filename):
    model_name = instance.__class__.__name__.lower()
    return f"{model_name}/{filename}"


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

    notes = models.TextField(blank=True, default='')
    manual_barcode = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("barcode number entered by user")
    )
    
    product_name = models.CharField(
        max_length=255,
        help_text=_("Full product name as shown on packaging")
    )

    package_size = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0.00,
        help_text=_("Number for the total package size")
    )
    package_size_unit = models.CharField(
        choices=UNIT_CHOICES,
        max_length=3,
        default="OTH",
        help_text=_("Unit for the total package size")
    )

    storage_condition = models.CharField(
        choices=STORAGE_CHOICES,
        max_length=12,
        default="shelf_stable",
        help_text=_("Required storage condition")
    )

    primary_package_material = models.CharField(
        choices=PACKAGING_CHOICES,
        max_length=15,
        default="other",
        help_text=_("Primary (touching the food) packaging")
    )

    secondary_package_material = models.CharField(
        choices=PACKAGING_CHOICES,
        blank=True,
        null=True,
        max_length=15,
        help_text=_("Secondary packaging (optional)")
    )

    source_batch = models.CharField(
        choices=BATCH_CHOICES,
        null=True,
        help_text=_("Product collection batch")
    )

    num_units = models.IntegerField(blank=True, null=True, help_text=_("Number of individual units (optional)"))

    is_variety_pack = models.BooleanField(
        default=False,
        help_text=_("Check if this is a variety/multi-pack product")
    )
    is_supplemented_food = models.BooleanField(
        default=False,
        help_text=_("Check if this is a Supplemented Food as defined by the regulations (whether or not it has a supplemental caution label)")
    )
    is_tds = models.BooleanField(
        default=False,
        help_text=_("Check if this product is part of the Total Diet Study")
    )
    is_individually_packaged = models.BooleanField(
        default=False,
        help_text=_("Check if this is multiple individually wrapped items. The important thing is if there is a physical wrapper around each individual object. It affects how the reference amount is applied")
    )
    has_preparation_instructions = models.BooleanField(
        default=False,
        help_text=_("Check if this has preparation instructions on the package")
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
    has_multiple_ingredients = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple LOI photos")
    )
    has_multiple_side_images = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple side of package photos")
    )
    has_multiple_other_images = models.BooleanField(
        default=False,
        help_text=_("Check if product has multiple other photos")
    )
    needs_manual_verification = models.BooleanField(
        default=False,
        help_text=_("Product is difficult to photograph clearly or otherwise classify, flag for manual verification")
    )
    # for supp foods
    has_supplemental_caution_id = models.BooleanField(default=False)
    has_nutrient_content_claim = models.BooleanField(default=False)
    has_nutrient_function_claim = models.BooleanField(default=False)
    has_disease_risk_reduction_claim = models.BooleanField(default=False)
    has_probiotic_claim = models.BooleanField(default=False)
    has_therapeutic_claim = models.BooleanField(default=False)
    has_function_claim = models.BooleanField(default=False)
    has_general_health_claim = models.BooleanField(default=False)
    has_quantitative_nutrient_declaration = models.BooleanField(default=False)
    has_implied_nonspecific_claim = models.BooleanField(default=False)
    has_logos_icons = models.BooleanField(default=False)
    has_third_party_label = models.BooleanField(default=False)

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


class AzureImageField(models.ImageField):
    def save_form_data(self, instance, data):
        try:
            super().save_form_data(instance, data)
        except AzureBlobStorageError as e:
            if getattr(instance, 'product', None) and instance.product.is_offline:
                instance.device_filename = data.name if data else None
                instance.is_uploaded = False
                instance.image = None
            else:
                raise ValidationError(_("Unable to save image: Azure storage error - {}").format(str(e)))


class BaseImageModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True,
        help_text=_("Any additional notes")
    )
    image = AzureImageField(
        upload_to=get_upload_path,
        help_text=_("Image file"),
        storage=AzureBlobStorage(),
        null=True,
        blank=True
    )
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
