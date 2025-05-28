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
            'is_supplemented_food',
            'is_variety_pack',
            'is_individually_packaged',
            'has_preparation_instructions',
            'has_front_of_pack_label',
            'has_multiple_nutrition_facts',
            'has_multiple_barcodes',
            'needs_manual_verification',
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
            'package_size_unit': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_supplemented_food': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_variety_pack': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_individually_packaged': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_preparation_instructions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_front_of_pack_label': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_nutrition_facts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_multiple_barcodes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_manual_verification': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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