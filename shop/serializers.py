# shop/serializers.py
from rest_framework import serializers
from .models import Product, CartItem, Cart, Order, OrderItem, Category


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        instance.user = validated_data.get('user', instance.user)
        instance.save()

        keep_items = []
        for item_data in items_data:
            if 'id' in item_data:
                item = CartItem.objects.get(id=item_data['id'], cart=instance)
                item.quantity = item_data.get('quantity', item.quantity)
                item.save()
                keep_items.append(item.id)
            else:
                item_data['cart'] = instance
                item = CartItem.objects.create(**item_data)
                keep_items.append(item.id)

        # Удаление старых элементов корзины, которые не были переданы в запросе
        for item in instance.items.all():
            if item.id not in keep_items:
                item.delete()

        return instance


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'items', 'created_at']


# shop/serializers.py
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
