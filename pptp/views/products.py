# views/products.py
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage
from ..forms.products import ProductSetupForm


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
        form.instance.created_by = self.get_user_from_headers()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('products:setup', kwargs={'pk': self.object.pk})

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