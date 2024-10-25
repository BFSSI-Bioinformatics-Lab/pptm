from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage


class ProductSetupForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'product_name',
            'is_variety_pack',
            'has_multiple_nutrition_facts',
            'has_multiple_barcodes',
        ]
        
    def clean_product_name(self):
        name = self.cleaned_data['product_name']
        if len(name.split()) < 2:
            raise forms.ValidationError(
                _("Please enter the full product name. For example: 'Honey Nut Cheerios' instead of just 'Cheerios'")
            )
        return name
    

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
