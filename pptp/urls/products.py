from django.urls import path
from ..views.products import (
    ProductDashboardView,
    ProductSubmissionStartView,
    CombinedUploadView,
    ajax_upload_image
)

app_name = 'products'

urlpatterns = [
    path('', ProductDashboardView.as_view(), name='dashboard'),
    path('submit/', ProductSubmissionStartView.as_view(), name='submission_start'),
    path('submit/<int:pk>/upload/', CombinedUploadView.as_view(), name='combined_upload'),
    path('submit/<int:pk>/ajax-upload/', ajax_upload_image, name='ajax_upload'),
]
