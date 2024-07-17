from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Product, Cart, CartItem, Order, OrderItem, Category
from .serializers import ProductSerializer, CartSerializer, OrderSerializer, CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_all_subcategories(self, category_id):
        """Рекурсивно получает все подкатегории для заданной категории."""
        subcategories = [category_id]
        direct_children = Category.objects.filter(parent_id=category_id)

        for child in direct_children:
            subcategories.extend(self.get_all_subcategories(child.id))

        return subcategories

    @swagger_auto_schema(
        method='post',
        operation_summary="Поиск продуктов по категории",
        operation_description="Получить список продуктов, отфильтрованных по указанному идентификатору категории и "
                              "всем её подкатегориям.",
        tags=['Product Search'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['category_id'],
            properties={
                'category_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Идентификатор категории')
            },
        ),
        responses={200: ProductSerializer(many=True)}
    )
    @action(detail=False, methods=['post'], url_path='by_category')
    def by_category(self, request):
        """Получает продукты по категории и всем её подкатегориям."""
        category_id = request.data.get('category_id')
        if category_id is None:
            return Response({'error': 'Идентификатор категории обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        all_subcategories = self.get_all_subcategories(category_id)
        products = self.queryset.filter(categories__id__in=all_subcategories)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID продукта'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Количество')
            },
            required=['product_id', 'quantity']
        ),
        responses={200: openapi.Response(description="Продукт добавлен в корзину")}
    )
    def create(self, request):
        """Добавление товара в корзину"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Продукт не найден"}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            cart_item.quantity += int(quantity)
        else:
            cart_item.quantity = int(quantity)

        cart_item.save()
        return Response({'status': 'Товар добавлен или обновлен'}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Обновить количество товара в корзине",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID продукта'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Количество')
            },
            required=['product_id', 'quantity']
        ),
        responses={200: openapi.Response(description="Количество товара в корзине обновлено")}
    )
    @action(detail=False, methods=['put'])
    def update_item(self, request):
        """Обновление количества товара в корзине"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Продукт не найден"}, status=status.HTTP_404_NOT_FOUND)

        cart = Cart.objects.get(user=request.user)
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            cart_item.quantity = quantity
            cart_item.save()
            return Response({'status': 'Количество товара в корзине обновлено'}, status=status.HTTP_200_OK)
        except CartItem.DoesNotExist:
            return Response({"error": "Товар не найден в корзине"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        method='delete',
        operation_description="Удалить товар из корзины",
        manual_parameters=[
            openapi.Parameter('product_id', openapi.IN_QUERY, description="ID продукта", type=openapi.TYPE_INTEGER)
        ],
        responses={200: openapi.Response(description="Товар удален из корзины")}
    )
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Удаление товара из корзины"""
        product_id = request.query_params.get('product_id')

        if not product_id:
            return Response({"error": "ID продукта обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        cart = Cart.objects.get(user=request.user)
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            cart_item.delete()
            return Response({'status': 'Товар удален'}, status=status.HTTP_200_OK)
        except CartItem.DoesNotExist:
            return Response({"error": "Товар не найден в корзине"}, status=status.HTTP_404_NOT_FOUND)


class OrderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            return Response({"error": "Невозможно создать заказ с пустой корзиной."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(user=request.user)
        items = [OrderItem(order=order, product=item.product, quantity=item.quantity) for item in cart.items.all()]
        OrderItem.objects.bulk_create(items)
        cart.items.all().delete()  # Очистить корзину после создания заказа
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryViewSet(mixins.CreateModelMixin,
                      mixins.DestroyModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent=None)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
