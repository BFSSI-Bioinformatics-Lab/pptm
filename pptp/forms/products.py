# forms/products.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage


class ProductSetupForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'product_name',
            'is_supplemented_food',
            'is_variety_pack',
            'is_individually_packaged',
            'has_preparation_instructions',
            'has_front_of_pack_label',
            'has_multiple_nutrition_facts',
            'has_multiple_barcodes',
        ]
        
    def clean_product_name(self):
        name = self.cleaned_data['product_name']
        if len(name.split()) < 2:
            raise forms.ValidationError(...)
        return name


class BarcodeUploadForm(forms.ModelForm):
    class Meta:
        model = Barcode
        fields = ['image', 'barcode_number', 'notes']


class NutritionFactsUploadForm(forms.ModelForm):
    class Meta:
        model = NutritionFacts
        fields = ['image', 'notes']


class IngredientsUploadForm(forms.ModelForm):
    class Meta:
        model = Ingredients
        fields = ['image', 'notes']


class ProductImageUploadForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'notes']