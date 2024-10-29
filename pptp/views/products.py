# views/products.py
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage
from ..forms.products import ProductSetupForm


class BaseProductStepView(LoginRequiredMixin):
    """Base class for all product submission steps"""
    view_step = None  # Will be set by child classes

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


class ProductSubmissionStartView(CreateView):
    model = Product
    fields = []
    template_name = 'pptp/products/submission_start.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('products:setup', kwargs={'pk': self.object.pk})


class ProductSetupView(BaseProductStepView, UpdateView):
    view_step = 0
    model = Product
    form_class = ProductSetupForm
    template_name = 'pptp/products/setup.html'
    
    def get_success_url(self):
        return reverse_lazy('products:barcode_upload', kwargs={'pk': self.object.pk})


class BarcodeUploadView(BaseProductStepView, CreateView):
    view_step = 1
    model = Barcode
    fields = ['barcode_image', 'barcode_number']
    template_name = 'pptp/products/barcode_upload.html'
    
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


class NutritionFactsUploadView(BaseProductStepView, CreateView):
    view_step = 2
    model = NutritionFacts
    fields = ['image', 'notes']
    template_name = 'pptp/products/nutrition_facts_upload.html'
    
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


class IngredientsUploadView(BaseProductStepView, CreateView):
    view_step = 3
    model = Ingredients
    fields = ['image', 'notes']
    template_name = 'pptp/products/ingredients_upload.html'
    
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


class ProductImagesUploadView(BaseProductStepView, CreateView):
    view_step = 4
    model = ProductImage
    fields = ['image', 'image_type', 'notes']
    template_name = 'pptp/products/product_images_upload.html'
    
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
    
    
class ProductReviewView(BaseProductStepView, UpdateView):
    view_step = 5
    model = Product
    template_name = 'pptp/products/review.html'
    fields = []  # No fields to update directly
    
    def is_previous_step_complete(self):
        # Require at least one ingredient image
        return self.product.ingredients.exists()
    
    def get_previous_step_url(self):
        return reverse_lazy('products:product_images_upload', kwargs={'pk': self.product.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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