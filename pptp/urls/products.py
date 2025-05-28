from django.urls import path
from ..views.products import (
    ProductDashboardView,
    CombinedUploadView,
    ajax_upload_image,
    validate_product_submission,
)

app_name = 'products'

urlpatterns = [
    path('', ProductDashboardView.as_view(), name='dashboard'),
    path('submit/', CombinedUploadView.as_view(), name='combined_upload_new'),
    path('submit/<int:pk>/', CombinedUploadView.as_view(), name='combined_upload_edit'),
    path('submit/<int:pk>/ajax-upload/', ajax_upload_image, name='ajax_upload'),
    path('submit/<int:pk>/validate/', validate_product_submission, name='validate_product')
]
