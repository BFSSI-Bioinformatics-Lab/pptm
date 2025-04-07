# views/products.py
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage
from ..forms.products import ProductSetupForm, BarcodeUploadForm, NutritionFactsUploadForm, IngredientsUploadForm, ProductImageUploadForm


class BaseProductView():
    """Base class for all product-related views"""
    def get_user_from_headers(self):
        return self.request.headers.get('Dh-User')

    def get_pending_upload_count(self):
        user = self.get_user_from_headers()
        return sum([
            Barcode.objects.filter(product__created_by=user, is_uploaded=False).count(),
            NutritionFacts.objects.filter(product__created_by=user, is_uploaded=False).count(),
            Ingredients.objects.filter(product__created_by=user, is_uploaded=False).count(),
            ProductImage.objects.filter(product__created_by=user, is_uploaded=False).count(),
        ])

class BaseProductTemplateView(BaseProductView):
    """Base class for views that render templates"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
    file_field_name = 'image'
    related_name = None
    upload_title = None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Set image_obj_list for the base template to use
        if self.related_name:
            context['image_obj_list'] = getattr(self.product, self.related_name).all()
        
        # Set upload title if provided
        if self.upload_title:
            context['upload_title'] = self.upload_title
            
        return context

    def form_valid(self, form):
        form.instance.product = self.product
        form.instance.is_uploaded = True
        return super().form_valid(form)


class ProductSetupView(BaseProductStepView, UpdateView):
    model = Product
    form_class = ProductSetupForm
    template_name = 'pptp/products/setup.html'
    view_step = 0
    
    def get_success_url(self):
        return reverse_lazy('products:barcode_upload', kwargs={'pk': self.object.pk})


class ProductSubmissionStartView(BaseProductStepView, CreateView):
    model = Product
    fields = []
    template_name = 'pptp/products/submission_start.html'
    view_step = -1

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('products:combined_upload', kwargs={'pk': self.object.pk})

    def is_previous_step_complete(self):
        return True

    def get_previous_step_url(self):
        return reverse_lazy('products:dashboard')

    def get_product(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.pop('product', None)
        return context


class BarcodeUploadView(BaseImageUploadView):
    view_step = 1
    model = Barcode
    fields = ['image', 'barcode_number']
    template_name = 'pptp/products/barcode_upload.html'
    related_name = 'barcodes'
    upload_title = _("Upload Product Barcodes")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add info about whether more barcodes are needed
        context['needs_more_barcodes'] = (
            self.product.has_multiple_barcodes and 
            self.product.barcodes.count() < 2
        )
        # Pass barcodes for backward compatibility with existing template
        context['barcodes'] = context['image_obj_list']
        return context

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
    related_name = 'nutrition_facts'  # Fix typo in "realted_name"
    upload_title = _("Upload Nutrition Facts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add info about whether more nutrition facts are needed
        context['needs_more_nutrition_facts'] = (
            self.product.has_multiple_nutrition_facts and 
            self.product.nutrition_facts.count() < 2
        )
        # Pass nutrition_facts for backward compatibility with existing template
        context['nutrition_facts'] = context['image_obj_list']
        return context

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
    upload_title = _("Upload Ingredients")

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
    upload_title = _("Upload Product Images")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Keep backward compatibility with existing template
        context['uploaded_images'] = [img for img in context['image_obj_list'] if img.is_uploaded]
        context['pending_images'] = [img for img in context['image_obj_list'] if not img.is_uploaded]
        return context

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


class CombinedUploadView(UpdateView):
    """A single page that combines all the upload steps with enhanced drag-and-drop functionality"""
    model = Product
    template_name = 'pptp/products/combined_upload.html'
    form_class = ProductSetupForm

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()
        
        product = self.get_object()
        
        return form_class(
            self.request.POST if self.request.method == "POST" else None, 
            self.request.FILES if self.request.method == "POST" else None, 
            instance=self.get_object()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add all existing images
        product = self.get_object()
        context['existing_barcodes'] = product.barcodes.all()
        context['existing_nutrition_facts'] = product.nutrition_facts.all()
        context['existing_ingredients'] = product.ingredients.all()
        
        # Group product images by type for clearer display
        product_images = product.product_images.all()
        product_images_by_type = {
            'front': product_images.filter(image_type='front'),
            'back': product_images.filter(image_type='back'),
            'side': product_images.filter(image_type='side'),
            'other': product_images.filter(image_type='other'),
        }
        context['product_images_by_type'] = product_images_by_type
        
        # Add empty forms for new uploads
        context['barcode_form'] = BarcodeUploadForm()
        context['nutrition_form'] = NutritionFactsUploadForm()
        context['ingredients_form'] = IngredientsUploadForm()
        context['product_image_form'] = ProductImageUploadForm()
        
        # Add data for validation
        context['validation_errors'] = self.get_validation_errors(product)
        
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()  # Set self.object explicitly
        form = self.get_form()
        
        if form.is_valid():
            self.object = form.save()  # Update self.object with saved instance
        else:
            return self.form_invalid(form)
        
        product = self.object
        # Process image uploads
        self.process_uploads(request, product)
        
        # Check if the user clicked submit
        if 'submit' in request.POST:
            # Validate submission
            errors = self.get_validation_errors(product)
            if errors:
                for error in errors:
                    messages.error(request, error)
                return self.get(request, *args, **kwargs)
            
            # Mark submission as complete
            product.submission_complete = True
            product.save()
            messages.success(request, _("Product submission completed successfully!"))
            return redirect('products:dashboard')
        
        # Default: stay on the same page with updates
        messages.success(request, _("Changes saved successfully."))
        return self.get(request, *args, **kwargs)
    
    def process_uploads(self, request, product):
        """Process all file uploads from the form"""
        # Helper function to save an upload
        def save_upload(form_class, prefix, related_name):
            # Look for regular and indexed form fields
            regular_form = None
            indexed_forms = []
            
            # Check for regular upload
            if any(request.FILES.get(f'{prefix}-{field}') for field in form_class().fields if field != 'notes'):
                regular_form = form_class(request.POST, request.FILES, prefix=prefix)
            
            # Check for indexed uploads (for multiple files)
            index = 0
            while True:
                prefix_idx = f'{prefix}-{index}'
                if any(request.FILES.get(f'{prefix_idx}-{field}') for field in form_class().fields if field != 'notes'):
                    indexed_forms.append(form_class(request.POST, request.FILES, prefix=prefix_idx))
                    index += 1
                else:
                    break
            
            # Process regular form
            if regular_form and regular_form.is_valid():
                instance = regular_form.save(commit=False)
                instance.product = product
                instance.is_uploaded = True
                instance.save()
            
            # Process indexed forms
            for form in indexed_forms:
                if form.is_valid():
                    instance = form.save(commit=False)
                    instance.product = product
                    instance.is_uploaded = True
                    instance.save()
            
            return bool(regular_form and regular_form.is_valid()) or any(form.is_valid() for form in indexed_forms)
        
        # Process each upload type
        upload_types = [
            (BarcodeUploadForm, 'barcode', 'barcode_number'),
            (NutritionFactsUploadForm, 'nutrition', None),
            (IngredientsUploadForm, 'ingredients', None),
        ]
        
        for form_class, prefix, related_field in upload_types:
            save_upload(form_class, prefix, related_field)
        
        # Handle product images (multiple types)
        image_types = ['front', 'back', 'side', 'other']
        for image_type in image_types:
            form = ProductImageUploadForm(request.POST, request.FILES, prefix=f'image_{image_type}')
            if form.is_valid() and request.FILES.get(f'image_{image_type}-image'):
                instance = form.save(commit=False)
                instance.product = product
                instance.image_type = image_type
                instance.is_uploaded = True
                instance.save()
    
    def get_validation_errors(self, product):
        """Check all requirements and return list of validation errors"""
        errors = []
        
        # Check product name
        if not product.product_name:
            errors.append(_("Product name is required"))
            
        # Check barcodes
        if not product.barcodes.exists():
            errors.append(_("At least one barcode image is required"))
        elif product.has_multiple_barcodes and product.barcodes.count() < 2:
            errors.append(_("Multiple barcodes were indicated but not all were uploaded"))
            
        # Check nutrition facts
        if not product.nutrition_facts.exists():
            errors.append(_("At least one nutrition facts image is required"))
        elif product.has_multiple_nutrition_facts and product.nutrition_facts.count() < 2:
            errors.append(_("Multiple nutrition facts were indicated but not all were uploaded"))
            
        # Check ingredients
        if not product.ingredients.exists():
            errors.append(_("At least one ingredients image is required"))
            
        # Check product images
        required_types = {'front', 'back'}
        existing_types = set(product.product_images.values_list('image_type', flat=True))
        missing_types = required_types - existing_types
        
        if missing_types:
            missing_types_display = [type.title() for type in missing_types]
            errors.append(_("Missing required product images: %s") % ", ".join(missing_types_display))
            
        return errors


@require_POST
def ajax_upload_image(request, pk):
    """Handle AJAX image uploads from drag and drop functionality"""
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': _("No file provided")})
    
    file_obj = request.FILES['file']
    image_type = request.POST.get('image_type')
    notes = request.POST.get('notes', '')
    
    if not image_type:
        return JsonResponse({'success': False, 'error': _("No image type specified")})
    
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': _("Product not found")})
    
    try:
        # Create the appropriate type of image
        if image_type == 'barcode':
            barcode_number = request.POST.get('barcode_number', '')
            image = Barcode.objects.create(
                product=product,
                image=file_obj,
                barcode_number=barcode_number,
                notes=notes,
                is_uploaded=True
            )
        elif image_type == 'nutrition':
            image = NutritionFacts.objects.create(
                product=product,
                image=file_obj,
                notes=notes,
                is_uploaded=True
            )
        elif image_type == 'ingredients':
            image = Ingredients.objects.create(
                product=product,
                image=file_obj,
                notes=notes,
                is_uploaded=True
            )
        elif image_type in ['front', 'back', 'side', 'other']:
            image = ProductImage.objects.create(
                product=product,
                image=file_obj,
                image_type=image_type,
                notes=notes,
                is_uploaded=True
            )
        else:
            return JsonResponse({'success': False, 'error': _("Invalid image type")})
        
        return JsonResponse({
            'success': True,
            'image_id': image.id,
            'image_url': image.image.url
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
