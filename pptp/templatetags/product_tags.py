# pptp/templatetags/product_tags.py
from django import template

register = template.Library()

@register.filter
def get_related_images(product):
    """Get all images related to a product based on the current view"""
    view_name = getattr(product, '_current_view', '')
    
    if 'barcode' in view_name.lower():
        return product.barcodes.all()
    elif 'nutrition' in view_name.lower():
        return product.nutrition_facts.all()
    elif 'ingredients' in view_name.lower():
        return product.ingredients.all()
    elif 'product_images' in view_name.lower():
        return product.product_images.all()
    return []
