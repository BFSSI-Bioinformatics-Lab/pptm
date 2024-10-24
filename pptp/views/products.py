from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DetailView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage
from ..forms.products import (
    BarcodeForm,
    NutritionFactsForm,
    IngredientsForm,
    ProductImageForm,
)


class ProductSubmissionStart(LoginRequiredMixin, CreateView):
    model = Product
    template_name = 'pptp/products/submission_start.html'
    fields = []  # No fields needed as we're just creating an empty product

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('products:barcode_upload', kwargs={'pk': self.object.pk})


class BarcodeUploadView(LoginRequiredMixin, CreateView):
    model = Barcode
    form_class = BarcodeForm
    template_name = 'pptp/products/barcode_upload.html'

    def form_valid(self, form):
        form.instance.product_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('products:nutrition_facts_upload', kwargs={'pk': self.kwargs['pk']})


class NutritionFactsUploadView(LoginRequiredMixin, CreateView):
    model = NutritionFacts
    form_class = NutritionFactsForm
    template_name = 'pptp/products/nutrition_facts_upload.html'

    def form_valid(self, form):
        form.instance.product_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('products:ingredients_upload', kwargs={'pk': self.kwargs['pk']})


class IngredientsUploadView(LoginRequiredMixin, CreateView):
    model = Ingredients
    form_class = IngredientsForm
    template_name = 'pptp/products/ingredients_upload.html'

    def form_valid(self, form):
        form.instance.product_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('products:product_images_upload', kwargs={'pk': self.kwargs['pk']})


class ProductImagesUploadView(LoginRequiredMixin, CreateView):
    model = ProductImage
    form_class = ProductImageForm
    template_name = 'pptp/products/product_images_upload.html'

    def form_valid(self, form):
        form.instance.product_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('products:review', kwargs={'pk': self.kwargs['pk']})


class ProductReviewView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'pptp/products/review.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add submission steps for progress bar
        context['submission_steps'] = [
            {'name': 'Start', 'completed': True, 'active': False},
            {'name': 'Barcodes', 'completed': True, 'active': False},
            {'name': 'Nutrition', 'completed': True, 'active': False},
            {'name': 'Ingredients', 'completed': True, 'active': False},
            {'name': 'Images', 'completed': True, 'active': False},
            {'name': 'Review', 'completed': False, 'active': True},
        ]
        
        # Check if we have all required data
        product = self.get_object()
        context['missing_items'] = []
        
        if not product.barcodes.exists():
            context['missing_items'].append('Barcode images')
        
        if not product.nutrition_facts.exists():
            context['missing_items'].append('Nutrition facts images')
            
        if not product.ingredients.exists():
            context['missing_items'].append('Ingredients images')
            
        if not product.product_images.exists():
            context['missing_items'].append('Product images')
            
        return context

    def post(self, request, *args, **kwargs):
        product = self.get_object()
        action = request.POST.get('action')

        if action == 'confirm':
            # Check if we have all required data
            if (product.barcodes.exists() and 
                product.nutrition_facts.exists() and 
                product.ingredients.exists() and 
                product.product_images.exists()):
                
                product.submission_complete = True
                product.save()
                messages.success(request, 'Product submission completed successfully!')
                return redirect('products:submission_start')  # Or wherever you want to redirect after completion
            else:
                messages.error(request, 'Please upload all required images before confirming.')
                return self.get(request, *args, **kwargs)

        # Handle edit redirects
        elif action == 'edit_barcodes':
            return redirect('products:barcode_upload', pk=product.pk)
        elif action == 'edit_nutrition':
            return redirect('products:nutrition_facts_upload', pk=product.pk)
        elif action == 'edit_ingredients':
            return redirect('products:ingredients_upload', pk=product.pk)
        elif action == 'edit_images':
            return redirect('products:product_images_upload', pk=product.pk)

        return self.get(request, *args, **kwargs)