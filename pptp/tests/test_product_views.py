from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import Product, Barcode, NutritionFacts, ProductImage

User = get_user_model()


class ProductUploadTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        self.client.login(email='test@example.com', password='testpass123')

        # Create a proper test image file
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        self.test_image = SimpleUploadedFile(
            name='test_image.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        # Create base product
        self.product = Product.objects.create(
            created_by=self.user,
            product_name='Test Product Name',
            is_variety_pack=False,
            has_multiple_nutrition_facts=False,
            has_multiple_barcodes=False
        )


class BarcodeUploadTests(ProductUploadTestCase):
    def test_single_barcode_upload_success(self):
        """Test successful upload of a single barcode when multiple not required"""
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        test_image = SimpleUploadedFile(
            name='barcode1.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:barcode_upload', kwargs={'pk': self.product.pk}),
            {
                'barcode_image': test_image,
                'barcode_number': '123456789',
                'continue': ''
            }
        )
        self.assertRedirects(
            response,
            reverse('products:nutrition_facts_upload', kwargs={'pk': self.product.pk})
        )
        self.assertEqual(self.product.barcodes.count(), 1)

    def test_multiple_barcodes_required_validation(self):
        """Test that system requires multiple barcodes when specified"""
        self.product.has_multiple_barcodes = True
        self.product.save()

        # Upload first barcode
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        first_image = SimpleUploadedFile(
            name='barcode2.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:barcode_upload', kwargs={'pk': self.product.pk}),
            {
                'barcode_image': first_image,
                'barcode_number': '123456789',
                'continue': ''
            }
        )
        
        # Should not proceed to next step with just one barcode
        self.assertRedirects(
            response,
            reverse('products:barcode_upload', kwargs={'pk': self.product.pk})
        )

        # Upload second barcode
        image_content2 = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        second_image = SimpleUploadedFile(
            name='barcode3.gif',
            content=image_content2,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:barcode_upload', kwargs={'pk': self.product.pk}),
            {
                'barcode_image': second_image,
                'barcode_number': '987654321',
                'continue': ''
            }
        )
        
        # Now should proceed to next step
        self.assertRedirects(
            response,
            reverse('products:nutrition_facts_upload', kwargs={'pk': self.product.pk})
        )
        self.assertEqual(self.product.barcodes.count(), 2)

        
class NutritionFactsUploadTests(ProductUploadTestCase):
    def setUp(self):
        super().setUp()
        # Add a barcode to satisfy previous step requirement
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        barcode_image = SimpleUploadedFile(
            name='barcode.gif',
            content=image_content,
            content_type='image/gif'
        )
        Barcode.objects.create(
            product=self.product,
            barcode_image=barcode_image,
            barcode_number='123456789'
        )

    def test_single_nutrition_facts_upload_success(self):
        """Test successful upload of a single nutrition facts table when multiple not required"""
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        test_image = SimpleUploadedFile(
            name='nutrition.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:nutrition_facts_upload', kwargs={'pk': self.product.pk}),
            {
                'image': test_image,
                'notes': 'Test notes',
                'continue': ''
            }
        )
        self.assertRedirects(
            response,
            reverse('products:ingredients_upload', kwargs={'pk': self.product.pk})
        )

    def test_multiple_nutrition_facts_required_validation(self):
        """Test that system requires multiple nutrition facts tables when specified"""
        self.product.has_multiple_nutrition_facts = True
        self.product.save()

        # Upload first nutrition facts table
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        test_image = SimpleUploadedFile(
            name='nutrition1.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:nutrition_facts_upload', kwargs={'pk': self.product.pk}),
            {
                'image': test_image,
                'notes': 'First table',
                'continue': ''
            }
        )
        
        # Should not redirect to next step
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('products:nutrition_facts_upload', kwargs={'pk': self.product.pk})
        )

        # Upload second nutrition facts table
        image_content2 = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        test_image2 = SimpleUploadedFile(
            name='nutrition2.gif',
            content=image_content2,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:nutrition_facts_upload', kwargs={'pk': self.product.pk}),
            {
                'image': test_image2,
                'notes': 'Second table',
                'continue': ''
            }
        )
        
        # Now should proceed to next step
        self.assertRedirects(
            response,
            reverse('products:ingredients_upload', kwargs={'pk': self.product.pk})
        )


class ProductImagesUploadTests(ProductUploadTestCase):
    def setUp(self):
        super().setUp()
        # Add required previous steps
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        
        # Add barcode
        barcode_image = SimpleUploadedFile(
            name='barcode.gif',
            content=image_content,
            content_type='image/gif'
        )
        Barcode.objects.create(
            product=self.product,
            barcode_image=barcode_image,
            barcode_number='123456789'
        )
        
        # Add nutrition facts
        nft_image = SimpleUploadedFile(
            name='nutrition.gif',
            content=image_content,
            content_type='image/gif'
        )
        NutritionFacts.objects.create(
            product=self.product,
            image=nft_image
        )
        
        # Add ingredients
        ing_image = SimpleUploadedFile(
            name='ingredients.gif',
            content=image_content,
            content_type='image/gif'
        )
        self.product.ingredients.create(
            image=ing_image
        )

    def test_product_images_required_types(self):
        """Test that system requires both front and back images"""
        # Upload front image
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        front_image = SimpleUploadedFile(
            name='front.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:product_images_upload', kwargs={'pk': self.product.pk}),
            {
                'image': front_image,
                'image_type': 'front',
                'notes': 'Front view',
                'continue': ''
            }
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('products:product_images_upload', kwargs={'pk': self.product.pk})
        )

        # Upload back image
        image_content2 = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        back_image = SimpleUploadedFile(
            name='back.gif',
            content=image_content2,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:product_images_upload', kwargs={'pk': self.product.pk}),
            {
                'image': back_image,
                'image_type': 'back',
                'notes': 'Back view',
                'continue': ''
            }
        )
        
        self.assertRedirects(
            response,
            reverse('products:review', kwargs={'pk': self.product.pk})
        )

    def test_optional_side_images(self):
        """Test that side images are optional but stored correctly"""
        # Upload required images first
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        front_image = SimpleUploadedFile(
            name='front.gif',
            content=image_content,
            content_type='image/gif'
        )
        ProductImage.objects.create(
            product=self.product,
            image=front_image,
            image_type='front'
        )

        image_content2 = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        back_image = SimpleUploadedFile(
            name='back.gif',
            content=image_content2,
            content_type='image/gif'
        )
        ProductImage.objects.create(
            product=self.product,
            image=back_image,
            image_type='back'
        )
        
        # Add optional side image
        image_content3 = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        side_image = SimpleUploadedFile(
            name='side.gif',
            content=image_content3,
            content_type='image/gif'
        )
        
        response = self.client.post(
            reverse('products:product_images_upload', kwargs={'pk': self.product.pk}),
            {
                'image': side_image,
                'image_type': 'side',
                'notes': 'Side view',
                'continue': ''
            }
        )
        
        self.assertRedirects(
            response,
            reverse('products:review', kwargs={'pk': self.product.pk})
        )
        self.assertEqual(self.product.product_images.count(), 3)
        self.assertTrue(
            self.product.product_images.filter(image_type='side').exists()
        )