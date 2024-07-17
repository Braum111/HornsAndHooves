# shop/serializers.py
from rest_framework import serializers
from .models import Product, CartItem, Cart, Order, OrderItem, Category


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategorySerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'children']


class CategoryTreeSerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']

    def get_parent(self, obj):
        if obj.parent is not None:
            return CategoryTreeSerializer(obj.parent, context=self.context).data
        return None


class ProductSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'categories']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        category_trees = [CategoryTreeSerializer(category).data for category in instance.categories.all()]
        rep['categories'] = category_trees
        return rep


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
