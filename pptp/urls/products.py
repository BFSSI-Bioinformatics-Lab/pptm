from django.urls import path
from ..views.products import (
    ProductSubmissionStart,
    BarcodeUploadView,
    IngredientsUploadView,
    NutritionFactsUploadView,
    ProductImagesUploadView,
    ProductReviewView
)

app_name = 'products'

urlpatterns = [
    path('submit/', ProductSubmissionStart.as_view(), name='submission_start'),
    path('<int:pk>/barcode/', BarcodeUploadView.as_view(), name='barcode_upload'),
    path('<int:pk>/ingredients/', IngredientsUploadView.as_view(), name='ingredients_upload'),
    path('<int:pk>/nft/', NutritionFactsUploadView.as_view(), name='nutrition_facts_upload'),
    path('<int:pk>/product_images/', ProductImagesUploadView.as_view(), name='product_images_upload'),
    path('<int:pk>/review/', ProductReviewView.as_view(), name='review'),
]