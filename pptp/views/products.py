# views/products.py
import os
import uuid
from django.views.generic import View, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage
from ..forms.products import ProductSetupForm


class BaseProductView(LoginRequiredMixin):
    """Base class for all product-related views"""
    
    def get_pending_upload_count(self):
        """Get total number of pending uploads for the user"""
        user = self.request.user
        return sum([
            Barcode.objects.filter(product__created_by=user, is_uploaded=False).count(),
            NutritionFacts.objects.filter(product__created_by=user, is_uploaded=False).count(),
            Ingredients.objects.filter(product__created_by=user, is_uploaded=False).count(),
            ProductImage.objects.filter(product__created_by=user, is_uploaded=False).count(),
        ])
    
    def get_common_context(self):
        """Get context data common to all product views"""
        return {
            'photo_queue_mode': self.request.session.get('photo_queue_mode', False),
            'pending_upload_count': self.get_pending_upload_count(),
        }


class BaseProductTemplateView(BaseProductView):
    """Base class for views that render templates"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_common_context())
        return context
    

class ProductDashboardView(BaseProductTemplateView, TemplateView):
    template_name = 'pptp/products/dashboard.html'


class BaseProductStepView(BaseProductTemplateView):
    """Base class for all product submission steps"""
    view_step = None  # Will be set by child classes
    template_name = 'pptp/products/base_submission.html'  # Default template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        context['view_step'] = self.view_step
        return context

    def dispatch(self, request, *args, **kwargs):
        self.product = self.get_product()
        
        if not self.is_previous_step_complete():
            messages.error(request, _("Please complete the previous step first."))
            return redirect(self.get_previous_step_url())
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_product(self):
        return Product.objects.get(pk=self.kwargs['pk'])
    
    def is_previous_step_complete(self):
        """Override in child classes to implement specific validation"""
        return True
    
    def get_previous_step_url(self):
        """Override in child classes to specify the previous step URL"""
        raise NotImplementedError


class BaseImageUploadView(BaseProductStepView, CreateView):
    """Base class specifically for image upload views"""
    template_name = 'pptp/products/image_upload_base.html'
    file_field_name = 'image'  # Default value, can be overridden
    related_name = None  # Must be set by child classes
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.related_name:
            # Split images into uploaded and pending
            queryset = getattr(self.product, self.related_name).all()
            context['uploaded_images'] = queryset.filter(is_uploaded=True)
            context['pending_images'] = queryset.filter(is_uploaded=False)
            context['is_offline_mode'] = self.request.session.get('photo_queue_mode', False)
        return context

    def form_valid(self, form):
        is_queue_mode = self.request.session.get('photo_queue_mode', False)
        form.instance.product = self.product
        
        if is_queue_mode:
            # In photo queue mode, just store the filename
            if file := self.request.FILES.get(self.file_field_name):
                form.instance.device_filename = file.name
                form.instance.is_uploaded = False
                # Don't save the actual file
                setattr(form.instance, self.file_field_name, None)
        else:
            # Normal mode - save the file
            form.instance.is_uploaded = True
            
        return super().form_valid(form)


class ProductSetupView(BaseProductStepView, UpdateView):
    model = Product
    form_class = ProductSetupForm
    template_name = 'pptp/products/setup.html'
    view_step = 0
    
    def get_success_url(self):
        return reverse_lazy('products:barcode_upload', kwargs={'pk': self.object.pk})


class TogglePhotoQueueMode(BaseProductView, View):
    def post(self, request):
        current_mode = request.session.get('photo_queue_mode', False)
        request.session['photo_queue_mode'] = not current_mode
        return redirect(request.META.get('HTTP_REFERER', 'products:dashboard'))

    def get(self, request):
        return redirect(request.META.get('HTTP_REFERER', 'products:dashboard'))


from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse


class BulkUploadView(LoginRequiredMixin, TemplateView):
    """
    Handle bulk image upload for offline mode products.
    Matches uploaded files with pending records and updates them.
    """
    template_name = 'pptp/products/bulk_upload.html'

    def get_pending_records(self):
        """Get all pending records that need file uploads."""
        pending_files = []
        models_to_check = [
            (Barcode, 'Barcode'),
            (NutritionFacts, 'Nutrition Facts'),
            (Ingredients, 'Ingredients'),
            (ProductImage, 'Product Image')
        ]
        
        for model, type_name in models_to_check:
            records = model.objects.filter(
                product__created_by=self.request.user,
                product__is_offline=True,
                is_uploaded=False
            ).select_related('product')
            
            for record in records:
                pending_files.append({
                    'filename': record.device_filename,
                    'type': type_name,
                    'product': record.product.product_name,
                    'id': record.id,
                    'model': model.__name__
                })
        
        return pending_files

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_files'] = self.get_pending_records()
        
        if 'upload_results' in self.request.session:
            context['results'] = self.request.session.pop('upload_results')
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle file upload and processing."""
        if not request.FILES:
            messages.error(request, _("No files were uploaded"))
            return redirect('products:bulk_upload')

        try:
            files = request.FILES.getlist('files')
            if not files:
                messages.error(request, _("No files were selected"))
                return redirect('products:bulk_upload')

            results = self.process_files(files)
            
            # Add summary messages
            if results['summary']['success'] > 0:
                messages.success(
                    request,
                    _("Successfully processed %(count)d files") % 
                    {'count': results['summary']['success']}
                )
            
            if results['summary']['failed'] > 0:
                messages.warning(
                    request,
                    _("Failed to process %(count)d files") % 
                    {'count': results['summary']['failed']}
                )

            request.session['upload_results'] = results
            
        except Exception as e:
            messages.error(request, _("Error processing files: %s") % str(e))
        
        return redirect('products:bulk_upload')

    def get_image_field_name(self, record):
        """Get the correct image field name based on record type."""
        if isinstance(record, Barcode):
            return 'barcode_image'
        return 'image'

    def check_product_completion(self, product):
        """Check if all required files for a product have been uploaded."""
        pending_uploads = any([
            product.barcodes.filter(is_uploaded=False).exists(),
            product.nutrition_facts.filter(is_uploaded=False).exists(),
            product.ingredients.filter(is_uploaded=False).exists(),
            product.product_images.filter(is_uploaded=False).exists()
        ])
        
        if not pending_uploads:
            product.is_offline = False
            product.save()
            
            messages.success(
                self.request,
                _("All files uploaded for product: %s") % product.product_name
            )

    @transaction.atomic
    def process_files(self, files):
        """
        Process uploaded files and match them with pending records.
        Returns dict with processing results.
        """
        results = {
            'processed': [],
            'errors': [],
            'summary': {
                'total': len(files),
                'success': 0,
                'failed': 0,
                'products_updated': set()
            }
        }

        # Create filename lookup
        filename_map = {f.name: f for f in files}
        
        # Get all relevant pending records in a single query
        models_to_check = [Barcode, NutritionFacts, Ingredients, ProductImage]
        pending_records = []
        
        for model in models_to_check:
            records = model.objects.filter(
                product__created_by=self.request.user,
                product__is_offline=True,
                is_uploaded=False,
                device_filename__in=filename_map.keys()
            ).select_related('product')
            pending_records.extend(records)

        # Track processed filenames
        processed_filenames = set()

        # Process records
        for record in pending_records:
            try:
                file = filename_map.get(record.device_filename)
                if not file:
                    continue

                field_name = self.get_image_field_name(record)
                setattr(record, field_name, file)
                record.is_uploaded = True
                record.save()

                processed_filenames.add(record.device_filename)
                results['processed'].append({
                    'filename': record.device_filename,
                    'product': record.product.product_name,
                    'type': record.__class__.__name__
                })
                results['summary']['success'] += 1
                results['summary']['products_updated'].add(record.product.id)

                self.check_product_completion(record.product)

            except Exception as e:
                results['errors'].append({
                    'filename': record.device_filename,
                    'error': str(e)
                })
                results['summary']['failed'] += 1

        # Handle unmatched files
        unmatched_files = set(filename_map.keys()) - processed_filenames
        for filename in unmatched_files:
            results['errors'].append({
                'filename': filename,
                'error': _('No matching pending upload found for this file')
            })
            results['summary']['failed'] += 1

        # Convert set to list for serialization
        results['summary']['products_updated'] = list(results['summary']['products_updated'])
        return results
    
    def get_image_field_name(self, record):
        """Get the correct image field name based on record type"""
        if isinstance(record, Barcode):
            return 'barcode_image'
        return 'image'

    def check_product_completion(self, product):
        """Check if all files for a product have been uploaded"""
        all_uploaded = not any([
            product.barcodes.filter(is_uploaded=False).exists(),
            product.nutrition_facts.filter(is_uploaded=False).exists(),
            product.ingredients.filter(is_uploaded=False).exists(),
            product.product_images.filter(is_uploaded=False).exists()
        ])
        
        if all_uploaded:
            product.is_offline = False
            product.save()


class ProductSubmissionStartView(BaseProductStepView, CreateView):
    model = Product
    fields = []
    template_name = 'pptp/products/submission_start.html'
    view_step = -1  # Setting this to -1 to indicate it's before step 0
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('products:setup', kwargs={'pk': self.object.pk})

    def is_previous_step_complete(self):
        # No previous step to complete
        return True
    
    def get_previous_step_url(self):
        return reverse_lazy('products:dashboard')
    
    def get_product(self):
        # Override to return None since we don't have a product yet
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Remove 'product' from context since we don't have one yet
        context.pop('product', None)
        return context


class BarcodeUploadView(BaseImageUploadView):
    view_step = 1
    model = Barcode
    fields = ['image', 'barcode_number']
    template_name = 'pptp/products/barcode_upload.html'
    related_name = 'barcodes'

    def is_previous_step_complete(self):
        return bool(self.product.product_name)
    
    def get_previous_step_url(self):
        return reverse_lazy('products:setup', kwargs={'pk': self.product.pk})
    
    def form_valid(self, form):
        form.instance.product = self.product
        response = super().form_valid(form)
        
        if self.should_proceed_to_next_step():
            return redirect(self.get_success_url())
        
        messages.success(self.request, _("Barcode uploaded successfully. Add another or continue."))
        return redirect('products:barcode_upload', pk=self.product.pk)
    
    def should_proceed_to_next_step(self):
        if 'continue' not in self.request.POST:
            return False
            
        if self.product.has_multiple_barcodes:
            barcode_count = self.product.barcodes.count()
            if barcode_count < 2:
                messages.error(self.request, _("Please upload at least 2 barcodes as indicated in setup."))
                return False
        return True
    
    def get_success_url(self):
        return reverse_lazy('products:nutrition_facts_upload', kwargs={'pk': self.product.pk})


class NutritionFactsUploadView(BaseImageUploadView):
    view_step = 2
    model = NutritionFacts
    fields = ['image', 'notes']
    template_name = 'pptp/products/nutrition_facts_upload.html'
    realted_name = 'nutrition_facts'

    def is_previous_step_complete(self):
        return self.product.barcodes.exists()
    
    def get_previous_step_url(self):
        return reverse_lazy('products:barcode_upload', kwargs={'pk': self.product.pk})
    
    def form_valid(self, form):
        form.instance.product = self.product
        response = super().form_valid(form)
        
        if self.should_proceed_to_next_step():
            return redirect(self.get_success_url())
        
        messages.success(self.request, _("Nutrition facts uploaded successfully. Add another or continue."))
        return redirect('products:nutrition_facts_upload', pk=self.product.pk)
    
    def should_proceed_to_next_step(self):
        if 'continue' not in self.request.POST:
            return False
            
        if self.product.has_multiple_nutrition_facts:
            nutrition_count = self.product.nutrition_facts.count()
            if nutrition_count < 2:
                messages.error(self.request, _("Please upload at least 2 nutrition facts tables as indicated in setup."))
                return False
        return True
    
    def get_success_url(self):
        return reverse_lazy('products:ingredients_upload', kwargs={'pk': self.product.pk})


class IngredientsUploadView(BaseImageUploadView):
    view_step = 3
    model = Ingredients
    fields = ['image', 'notes']
    template_name = 'pptp/products/ingredients_upload.html'
    related_name = 'ingredients'

    def is_previous_step_complete(self):
        return self.product.nutrition_facts.exists()
    
    def get_previous_step_url(self):
        return reverse_lazy('products:nutrition_facts_upload', kwargs={'pk': self.product.pk})
    
    def form_valid(self, form):
        form.instance.product = self.product
        response = super().form_valid(form)
        
        if 'continue' in self.request.POST:
            return redirect(self.get_success_url())
        
        messages.success(self.request, _("Ingredients image uploaded successfully. Add another or continue."))
        return redirect('products:ingredients_upload', pk=self.product.pk)
    
    def get_success_url(self):
        return reverse_lazy('products:product_images_upload', kwargs={'pk': self.product.pk})


class ProductImagesUploadView(BaseImageUploadView):
    view_step = 4
    model = ProductImage
    fields = ['image', 'image_type', 'notes']
    template_name = 'pptp/products/product_images_upload.html'
    related_name = 'product_images'

    def is_previous_step_complete(self):
        return self.product.ingredients.exists()
    
    def get_previous_step_url(self):
        return reverse_lazy('products:ingredients_upload', kwargs={'pk': self.product.pk})
    
    def form_valid(self, form):
        form.instance.product = self.product
        response = super().form_valid(form)
        
        if 'continue' in self.request.POST and self.should_proceed_to_next_step():
            return redirect(self.get_success_url())
        
        messages.success(self.request, _("Product image uploaded successfully. Add another or continue."))
        return redirect('products:product_images_upload', pk=self.product.pk)
    
    def should_proceed_to_next_step(self):
        required_types = set(['front', 'back'])
        existing_types = set(self.product.product_images.values_list('image_type', flat=True))
        
        if not required_types.issubset(existing_types):
            messages.error(self.request, _("Please upload at least one front and one back image of the product."))
            return False
        return True
    
    def get_success_url(self):
        return reverse_lazy('products:review', kwargs={'pk': self.product.pk})
    
    
class ProductReviewView(BaseProductView, UpdateView):
    view_step = 5
    model = Product
    template_name = 'pptp/products/review.html'
    fields = []  # No fields to update directly
    
    def dispatch(self, request, *args, **kwargs):
        self.product = Product.objects.get(pk=self.kwargs['pk'])
        
        if not self.product.ingredients.exists():
            messages.error(request, _("Please complete the previous step first."))
            return redirect('products:product_images_upload', pk=self.product.pk)
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        context['view_step'] = self.view_step
        context['validation_errors'] = self.get_validation_errors()
        
        # Group product images by type for display
        images_by_type = {}
        for image in self.product.product_images.all():
            image_type = image.get_image_type_display()
            if image_type not in images_by_type:
                images_by_type[image_type] = []
            images_by_type[image_type].append(image)
        context['images_by_type'] = images_by_type
        
        return context
    
    def get_validation_errors(self):
        """Check all requirements and return list of validation errors"""
        errors = []
        
        # Check product name
        if not self.product.product_name:
            errors.append(_("Product name is required"))
            
        # Check barcodes
        if not self.product.barcodes.exists():
            errors.append(_("At least one barcode image is required"))
        elif self.product.has_multiple_barcodes and self.product.barcodes.count() < 2:
            errors.append(_("Multiple barcodes were indicated but not all were uploaded"))
            
        # Check nutrition facts
        if not self.product.nutrition_facts.exists():
            errors.append(_("At least one nutrition facts image is required"))
        elif self.product.has_multiple_nutrition_facts and self.product.nutrition_facts.count() < 2:
            errors.append(_("Multiple nutrition facts were indicated but not all were uploaded"))
            
        # Check ingredients
        if not self.product.ingredients.exists():
            errors.append(_("At least one ingredients image is required"))
            
        # Check product images
        required_types = {'front', 'back'}
        existing_types = set(self.product.product_images.values_list('image_type', flat=True))
        missing_types = required_types - existing_types
        
        if missing_types:
            missing_types_display = [type.title() for type in missing_types]
            errors.append(_("Missing required product images: %s") % ", ".join(missing_types_display))
            
        return errors
    
    def post(self, request, *args, **kwargs):
        errors = self.get_validation_errors()
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return self.get(request, *args, **kwargs)
        
        # Mark submission as complete
        self.product.submission_complete = True
        self.product.save()
        
        messages.success(request, _("Product submission completed successfully!"))
        return redirect('products:submission_start')