from django import forms
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage

class BarcodeForm(forms.ModelForm):
    class Meta:
        model = Barcode
        fields = ['barcode_image']

class NutritionFactsForm(forms.ModelForm):
    class Meta:
        model = NutritionFacts
        fields = ['image', 'notes']

class IngredientsForm(forms.ModelForm):
    class Meta:
        model = Ingredients
        fields = ['image', 'notes']

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'image_type', 'notes']