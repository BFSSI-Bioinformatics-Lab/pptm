from django.urls import path
from ..views.products import (
    ProductDashboardView,
    ProductSetupView,
    ProductSubmissionStartView,
    BarcodeUploadView,
    IngredientsUploadView,
    NutritionFactsUploadView,
    ProductImagesUploadView,
    ProductReviewView,
    CombinedUploadView
)

app_name = 'products'

urlpatterns = [
    path('', ProductDashboardView.as_view(), name='dashboard'),
    path('submit/', ProductSubmissionStartView.as_view(), name='submission_start'),
    path('submit/<int:pk>/upload/', CombinedUploadView.as_view(), name='combined_upload'),
    path('submit/<int:pk>/setup/', ProductSetupView.as_view(), name='setup'),
    path('submit/<int:pk>/barcode/', BarcodeUploadView.as_view(), name='barcode_upload'),
    path('<int:pk>/ingredients/', IngredientsUploadView.as_view(), name='ingredients_upload'),
    path('<int:pk>/nft/', NutritionFactsUploadView.as_view(), name='nutrition_facts_upload'),
    path('<int:pk>/product_images/', ProductImagesUploadView.as_view(), name='product_images_upload'),
    path('<int:pk>/review/', ProductReviewView.as_view(), name='review')
]
