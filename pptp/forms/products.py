# forms/products.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Product


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
            raise forms.ValidationError(
                _("Please enter the full product name. For example: 'Honey Nut Cheerios' instead of just 'Cheerios'")
            )
        return name