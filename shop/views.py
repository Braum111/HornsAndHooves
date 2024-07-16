from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Product, Cart, CartItem, Order, OrderItem, Category
from .serializers import ProductSerializer, CartSerializer, OrderSerializer, CategorySerializer


class ProductViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        method='post',
        operation_description="Retrieve products by category",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Category ID')
            },
            required=['category_id']
        ),
        responses={200: ProductSerializer(many=True)}
    )
    @action(detail=False, methods=['post'], url_path='by_category')
    def by_category(self, request):
        category_id = request.data.get('category_id')
        if not category_id:
            return Response({"error": "Category ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        products = Product.objects.filter(category_id=category_id)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    # Используем GET для получения детальной информации о конкретном продукте
    def retrieve(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение корзины текущего пользователя",
        responses={200: CartSerializer(many=True)}
    )
    def list(self, request):
        """Получение корзины текущего пользователя"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Добавить продукт в корзину пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Product ID'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity')
            },
            required=['product_id', 'quantity']
        ),
        responses={200: openapi.Response(description="Product added to cart")}
    )
    def create(self, request):
        """Добавление товара в корзину"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            cart_item.quantity += int(quantity)
        else:
            cart_item.quantity = int(quantity)

        cart_item.save()
        return Response({'status': 'item added or updated'}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Обновить количество товара в корзине",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Product ID'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity')
            },
            required=['product_id', 'quantity']
        ),
        responses={200: openapi.Response(description="Product quantity updated")}
    )
    @action(detail=False, methods=['put'])
    def update_item(self, request):
        """Обновление количества товара в корзине"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        cart = Cart.objects.get(user=request.user)
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            cart_item.quantity = quantity
            cart_item.save()
            return Response({'status': 'cart item updated'}, status=status.HTTP_200_OK)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        method='delete',
        operation_description="Удалить товар из корзины",
        manual_parameters=[
            openapi.Parameter('product_id', openapi.IN_QUERY, description="Product ID", type=openapi.TYPE_INTEGER)
        ],
        responses={200: openapi.Response(description="Product removed from cart")}
    )
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Удаление товара из корзины"""
        product_id = request.query_params.get('product_id')

        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        cart = Cart.objects.get(user=request.user)
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            cart_item.delete()
            return Response({'status': 'item removed'}, status=status.HTTP_200_OK)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

class OrderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            return Response({"error": "Cannot create order with an empty cart."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(user=request.user)
        items = [OrderItem(order=order, product=item.product, quantity=item.quantity) for item in cart.items.all()]
        OrderItem.objects.bulk_create(items)
        cart.items.all().delete()  # Clear the cart after creating the order
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
