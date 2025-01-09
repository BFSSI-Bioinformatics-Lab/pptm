from django.contrib import admin
from .models.products import Product, Barcode, NutritionFacts, Ingredients, ProductImage

admin.site.register(Product)
admin.site.register(Barcode)
admin.site.register(NutritionFacts)
admin.site.register(Ingredients) 
admin.site.register(ProductImage)