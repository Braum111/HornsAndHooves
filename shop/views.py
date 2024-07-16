from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .serializers import CategorySerializer, ProductSerializer, CartSerializer, OrderSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @action(detail=False, methods=['post'])
    def by_category(self, request):
        category_id = request.data.get('category_id')
        products = Product.objects.filter(category_id=category_id)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='my_cart')
    def my_cart(self, request):
        cart = Cart.objects.get(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add_item')
    def add_item(self, request, pk=None):
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        product = Product.objects.get(id=product_id)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += int(quantity)
        else:
            cart_item.quantity = int(quantity)
        cart_item.save()
        return Response({'status': 'item added'})

    @action(detail=True, methods=['delete'], url_path='remove_item')
    def remove_item(self, request, pk=None):
        cart = self.get_object()
        product_id = request.data.get('product_id')
        product = Product.objects.get(id=product_id)
        CartItem.objects.filter(cart=cart, product=product).delete()
        return Response({'status': 'item removed'})

    @action(detail=True, methods=['put'], url_path='update_items')
    def update_items(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        cart = Cart.objects.get(user=user)

        if not cart.items.exists():
            return Response({"error": "Cannot create order with an empty cart."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(user=user)
        for item in cart.items.all():
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
        cart.items.all().delete()
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
