# views/products.py
from datetime import timedelta
from django.views.generic import View, UpdateView, TemplateView
from django.db import transaction
from django.db.models import Count
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import Product, Barcode, NutritionFacts, Ingredients, ProductImage
from ..forms.products import ProductSetupForm, BarcodeUploadForm, NutritionFactsUploadForm, IngredientsUploadForm, ProductImageUploadForm


class BaseProductView(LoginRequiredMixin):
    """Base class for all product-related views"""
    def get_user_from_headers(self):
        return self.request.headers.get('Dh-User')


class BaseProductTemplateView(BaseProductView, TemplateView):
    """Base class for views that render templates"""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ProductDashboardView(BaseProductTemplateView):
    template_name = 'pptp/products/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = self.get_user_from_headers()
        
        # Get all user's products
        user_products = Product.objects.filter(created_by=username)
        
        # Basic statistics
        context['total_products'] = user_products.count()
        context['completed_products'] = user_products.filter(submission_complete=True).count()
        context['incomplete_products'] = context['total_products'] - context['completed_products']
        
        # Special product types
        context['variety_packs'] = user_products.filter(is_variety_pack=True).count()
        context['supplemented_foods'] = user_products.filter(is_supplemented_food=True).count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['recent_products'] = user_products.filter(created_at__gte=thirty_days_ago).count()
        
        # Products by image type count
        products_with_images = user_products.annotate(
            image_count=Count('product_images')
        ).filter(image_count__gt=0).count()
        context['products_with_images'] = products_with_images
        
        # Products with multiple nutrition facts or barcodes
        context['multi_nutrition_products'] = user_products.filter(has_multiple_nutrition_facts=True).count()
        context['multi_barcode_products'] = user_products.filter(has_multiple_barcodes=True).count()
        
        # Offline vs online submissions
        context['offline_products'] = user_products.filter(is_offline=True).count()
        context['online_products'] = user_products.filter(is_offline=False).count()
        
        # Recent submissions (limited to 5)
        context['recent_submissions'] = user_products.order_by('-created_at')[:5]
        
        return context


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


class ProductSetupView(BaseProductStepView, UpdateView):
    model = Product
    form_class = ProductSetupForm
    template_name = 'pptp/products/setup.html'

    def get_success_url(self):
        return reverse_lazy('products:barcode_upload', kwargs={'pk': self.object.pk})


class CombinedUploadView(LoginRequiredMixin, View):
    """A single page that combines all the upload steps with enhanced drag-and-drop functionality"""
    template_name = 'pptp/products/combined_upload.html'

    def get(self, request, pk=None):
        if pk:
            # Editing existing product
            product = get_object_or_404(Product, pk=pk)
            form = ProductSetupForm(instance=product)
            is_editing = True
        else:
            # Creating new product - create it immediately so we have an ID for AJAX
            product = Product.objects.create(
                created_by=request.user.username,
                product_name="",  # Will be filled in by form
            )
            # Redirect to edit URL so we have a proper ID
            return redirect('products:combined_upload_edit', pk=product.pk)

        context = self.get_context_data(product, form, is_editing)
        return render(request, self.template_name, context) 

    def post(self, request, pk=None):
        if pk:
            product = get_object_or_404(Product, pk=pk)
            form = ProductSetupForm(request.POST, instance=product)
            is_editing = True
        else:
            form = ProductSetupForm(request.POST)
            product = None
            is_editing = False

        is_submit = 'submit_product' in request.POST

        if form.is_valid():
            with transaction.atomic():
                if not is_editing:
                    form.instance.created_by = request.user.username

                product = form.save()
                upload_errors = self.process_uploads(request, product)

                if upload_errors:
                    for error in upload_errors:
                        messages.error(request, error)
                    context = self.get_context_data(product, form, is_editing)
                    return render(request, self.template_name, context)

                if is_submit:
                    validation_errors = self.get_validation_errors(product)
                    if validation_errors:
                        for error in validation_errors:
                            messages.error(request, error)
                        context = self.get_context_data(product, form, is_editing)
                        return render(request, self.template_name, context)

                    product.submission_complete = True
                    product.save()
                    messages.success(request, _("Product submission completed successfully!"))
                    return redirect('products:dashboard')

                if is_editing:
                    messages.success(request, _("Product updated successfully."))
                else:
                    messages.success(request, _("Product created and saved successfully."))

                return redirect('products:combined_upload_edit', pk=product.pk)

        else:
            if product:
                try:
                    self.process_uploads(request, product)
                except:
                    pass

            messages.error(request, _("Please correct the errors below."))
            context = self.get_context_data(product, form, is_editing)
            return render(request, self.template_name, context)

    def get_context_data(self, product, form, is_editing):
        """Build context data for the template"""
        context = {
            'product': product,
            'form': form,
            'is_editing': is_editing,
            'view_step': 'combined_upload'
        }

        if product:
            context.update({
                'existing_barcodes': product.barcodes.all(),
                'existing_nutrition_facts': product.nutrition_facts.all(),
                'existing_ingredients': product.ingredients.all(),
                'product_images_by_type': {
                    'front': product.product_images.filter(image_type='front'),
                    'back': product.product_images.filter(image_type='back'),
                    'side': product.product_images.filter(image_type='side'),
                    'other': product.product_images.filter(image_type='other'),
                },
                'validation_errors': self.get_validation_errors(product)
            })
        else:
            context.update({
                'existing_barcodes': [],
                'existing_nutrition_facts': [],
                'existing_ingredients': [],
                'product_images_by_type': {
                    'front': [], 'back': [], 'side': [], 'other': []
                },
                'validation_errors': []
            })

        context.update({
            'barcode_form': BarcodeUploadForm(),
            'nutrition_form': NutritionFactsUploadForm(),
            'ingredients_form': IngredientsUploadForm(),
            'product_image_form': ProductImageUploadForm(),
        })

        return context
    
    def process_uploads(self, request, product):
        """Process all file uploads from the form, return list of errors"""
        errors = []
        
        def process_upload(form_class, prefix, is_product_image=False, image_type=None):
            if request.POST.get(f'{prefix}-already_uploaded') == 'true':
                return None
                
            has_file = request.FILES.get(f'{prefix}-image')
            if not has_file:
                return None
                
            form = form_class(request.POST, request.FILES, prefix=prefix)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.product = product
                instance.is_uploaded = True
                
                if is_product_image and image_type:
                    instance.image_type = image_type
                    
                instance.save()
                return None
            else:
                return f"Error uploading {prefix}: {form.errors}"
        
        def process_indexed_uploads(form_class, base_prefix):
            index = 0
            while True:
                prefix = f'{base_prefix}-{index}'
                
                if request.POST.get(f'{prefix}-already_uploaded') == 'true':
                    index += 1
                    continue
                    
                has_file = request.FILES.get(f'{prefix}-image')
                if not has_file:
                    break
                    
                form = form_class(request.POST, request.FILES, prefix=prefix)
                if form.is_valid():
                    instance = form.save(commit=False)
                    instance.product = product
                    instance.is_uploaded = True
                    instance.save()
                else:
                    errors.append(f"Error uploading {prefix}: {form.errors}")
                
                index += 1
        
        for form_class, prefix in [
            (BarcodeUploadForm, 'barcode'),
            (NutritionFactsUploadForm, 'nutrition'),
            (IngredientsUploadForm, 'ingredients')
        ]:
            error = process_upload(form_class, prefix)
            if error:
                errors.append(error)
        
        process_indexed_uploads(BarcodeUploadForm, 'barcode')
        process_indexed_uploads(NutritionFactsUploadForm, 'nutrition')
        process_indexed_uploads(IngredientsUploadForm, 'ingredients')
        
        for image_type in ['front', 'back', 'side', 'other']:
            error = process_upload(
                ProductImageUploadForm, 
                f'image_{image_type}', 
                is_product_image=True,
                image_type=image_type
            )
            if error:
                errors.append(error)
                
        return errors

    def get_validation_errors(self, product):
        """Check all requirements and return list of validation errors"""
        errors = []

        if not product.product_name:
            errors.append(_("Product name is required"))
        elif len(product.product_name.split()) < 2:
            errors.append(_("Please enter the full product name (at least two words)"))

        if not product.barcodes.exists():
            errors.append(_("At least one barcode image is required"))
        elif product.has_multiple_barcodes and product.barcodes.count() < 2:
            errors.append(_("Multiple barcodes were indicated but not all were uploaded"))

        if not product.nutrition_facts.exists():
            errors.append(_("At least one nutrition facts image is required"))
        elif product.has_multiple_nutrition_facts and product.nutrition_facts.count() < 2:
            errors.append(_("Multiple nutrition facts were indicated but not all were uploaded"))

        if not product.ingredients.exists():
            errors.append(_("At least one ingredients image is required"))

        required_types = {'front', 'back'}
        existing_types = set(product.product_images.values_list('image_type', flat=True))
        missing_types = required_types - existing_types

        if missing_types:
            missing_types_display = [type.title() for type in missing_types]
            errors.append(_("Missing required product images: %s") % ", ".join(missing_types_display))

        return errors

@require_POST
@transaction.atomic
def ajax_upload_image(request, pk):
    """Handle AJAX image uploads from drag and drop functionality"""
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': _("No file provided")})

    file_obj = request.FILES['file']
    image_type = request.POST.get('image_type')
    
    if not image_type:
        return JsonResponse({'success': False, 'error': _("No image type specified")})

    try:
        product = get_object_or_404(Product, pk=pk)
        notes = request.POST.get('notes', '')
        
        # Create the appropriate type of image based on image_type
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
            'image_url': image.image.url,
            'image_type': image_type
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def validate_product_submission(request, pk):
    """
    AJAX endpoint to validate product submission before final submission
    Returns errors as JSON that can be displayed to the user
    """

    try:
        product = Product.objects.get(pk=pk)

        view = CombinedUploadView()
        errors = view.get_validation_errors(product)

        return JsonResponse({
            'valid': len(errors) == 0,
            'errors': errors
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'errors': [_("Product not found")]
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'errors': [str(e)]
        }, status=500)
