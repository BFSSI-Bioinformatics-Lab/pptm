from django.urls import path
from ..views.products import (
    ProductDashboardView,
    TogglePhotoQueueMode,
    ProductSetupView,
    ProductSubmissionStartView,
    BarcodeUploadView,
    IngredientsUploadView,
    NutritionFactsUploadView,
    ProductImagesUploadView,
    ProductReviewView,
    BulkUploadView,
    TestCorsView
)

app_name = 'products'

urlpatterns = [
    path('', ProductDashboardView.as_view(), name='dashboard'),
    path('toggle-photo-queue/', TogglePhotoQueueMode.as_view(), name='toggle_photo_queue'),
    path('bulk-upload/', BulkUploadView.as_view(), name='bulk_upload'),
    path('submit/', ProductSubmissionStartView.as_view(), name='submission_start'),
    path('submit/<int:pk>/setup/', ProductSetupView.as_view(), name='setup'),
    path('submit/<int:pk>/barcode/', BarcodeUploadView.as_view(), name='barcode_upload'),
    path('<int:pk>/ingredients/', IngredientsUploadView.as_view(), name='ingredients_upload'),
    path('<int:pk>/nft/', NutritionFactsUploadView.as_view(), name='nutrition_facts_upload'),
    path('<int:pk>/product_images/', ProductImagesUploadView.as_view(), name='product_images_upload'),
    path('<int:pk>/review/', ProductReviewView.as_view(), name='review'),
    path('test-cors/', TestCorsView.as_view(), name='test_cors'),
]
