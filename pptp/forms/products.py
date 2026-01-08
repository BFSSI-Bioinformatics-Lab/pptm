from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage


class BaseUploadForm(forms.ModelForm):
    """Base form class for all image upload forms with common functionality"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'accept': 'image/*'
                })
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({
                    'class': 'form-control form-control-sm'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'form-control form-control-sm',
                    'rows': '1',
                    'placeholder': _('Notes (optional)')
                })


class ProductSetupForm(forms.ModelForm):
    """Form for basic product setup information"""
    
    class Meta:
        model = Product
        fields = [
            'product_name',
            'package_size',
            'package_size_unit',
            'num_units',
            'storage_condition',
            'primary_package_material',
            'secondary_package_material',
            'source_batch',
            'is_variety_pack',
            'is_individually_packaged',
            'has_preparation_instructions',
            'has_front_of_pack_label',
            'has_multiple_nutrition_facts',
            'has_multiple_barcodes',
            'has_multiple_ingredients',
            'has_multiple_side_images',
            'has_multiple_other_images',
            'needs_manual_verification',
            'has_supplemental_caution_id',
            'has_nutrient_content_claim',
            'has_nutrient_function_claim',
            'has_disease_risk_reduction_claim',
            'has_probiotic_claim',
            'has_therapeutic_claim',
            'has_function_claim',
            'has_general_health_claim',
            'has_quantitative_nutrient_declaration',
            'has_implied_nonspecific_claim',
            'has_logos_icons',
            'has_third_party_label',
            'notes',
            'manual_barcode'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter complete product name as shown on packaging')
            }),
            'package_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter package size (number only)'),
                'step': '0.01',
                'min': '0'
            }),
            'num_units': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Number of units (optional)')
            }),
            'package_size_unit': forms.Select(attrs={
                'class': 'form-select'
            }),
            'storage_condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'primary_package_material': forms.Select(attrs={
                'class': 'form-select'
            }),
            'secondary_package_material': forms.Select(attrs={
                'class': 'form-select'
            }),
            'source_batch': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_variety_pack': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_individually_packaged': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_preparation_instructions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_front_of_pack_label': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_nutrition_facts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_barcodes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_ingredients': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_side_images': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_other_images': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_manual_verification': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_supplemental_caution_id': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_nutrient_content_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_nutrient_function_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_disease_risk_reduction_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_probiotic_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_therapeutic_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_function_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_general_health_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_quantitative_nutrient_declaration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_implied_nonspecific_claim': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_logos_icons': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_third_party_label': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '4',
                'placeholder': _('Add any notes that will be necessary for assessing this product label that are not captured by the photos')
            }),
            'manual_barcode': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _('Enter barcode number (optional)'),
                'maxlength': '50'
            }),
        }
    
    def clean_product_name(self):
        name = self.cleaned_data['product_name']
        if len(name.split()) < 2:
            raise forms.ValidationError(_("Please enter the full product name (at least two words)"))
        return name


class BarcodeUploadForm(BaseUploadForm):
    """Form for uploading barcode images"""
    
    class Meta:
        model = Barcode
        fields = ['image', 'barcode_number', 'notes']
        widgets = {
            'barcode_number': forms.TextInput(attrs={
                'placeholder': _('Barcode number (optional)')
            })
        }


class NutritionFactsUploadForm(BaseUploadForm):
    """Form for uploading nutrition facts images"""
    
    class Meta:
        model = NutritionFacts
        fields = ['image', 'notes']


class IngredientsUploadForm(BaseUploadForm):
    """Form for uploading ingredients images"""
    
    class Meta:
        model = Ingredients
        fields = ['image', 'notes']


class ProductImageUploadForm(BaseUploadForm):
    """Form for uploading product images (front, back, side, etc.)"""
    
    class Meta:
        model = ProductImage
        fields = ['image', 'notes']