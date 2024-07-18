from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import Product, Cart, CartItem, Order, OrderItem, Category


class ProductViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='Electronics')
        # Сначала создаем продукт без указания категорий
        self.product = Product.objects.create(name='Laptop', description='A powerful laptop', price=1200)
        # После создания продукта устанавливаем категории с использованием .set()
        self.product.categories.set([self.category])

        self.client.login(username='testuser', password='12345')

    def test_list_products(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_product(self):
        url = reverse('product-detail', args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_price_and_category(self):
        url = reverse('product-filter-by-price-category')
        response = self.client.get(url, {'min_price': 1000, 'max_price': 1500, 'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product(self):
        url = reverse('product-list')
        data = {'name': 'Smartphone', 'description': 'Latest model', 'price': 700, 'categories': [self.category.id]}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_product(self):
        url = reverse('product-detail', args=[self.product.id])
        # Проверьте, что все необходимые поля включены в данные
        data = {'name': 'Updated Laptop', 'description': 'Updated description', 'price': 1250,
                'categories': [self.category.id]}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_product(self):
        url = reverse('product-detail', args=[self.product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CartViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cartuser', password='12345')
        self.client.login(username='cartuser', password='12345')
        self.product = Product.objects.create(name='Tablet', description='An Android tablet', price=300)

    def test_add_item_to_cart(self):
        url = reverse('cart-list')  # Предполагая, что добавление товара происходит здесь
        data = {'product_id': self.product.id, 'quantity': 1}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_cart(self):
        # Сначала добавим товар в корзину
        self.test_add_item_to_cart()
        url = reverse('cart-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_remove_item_from_cart(self):
        # Предполагаем, что товар уже добавлен в корзину
        self.test_add_item_to_cart()
        # URL, возможно, ожидает параметры через строку запроса
        url = reverse('cart-remove-item') + f'?product_id={self.product.id}'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_cart_item(self):
        # Сначала добавим товар в корзину
        self.test_add_item_to_cart()
        url = reverse('cart-update-item')
        data = {'product_id': self.product.id, 'quantity': 3}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
