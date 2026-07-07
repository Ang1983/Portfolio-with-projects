from rest_framework import serializers 
from .models import (
    Employee, Cashier, Shift, 
    LoyaltyCard, Drink, Syrup, 
    Coupon, Receipt, TimeScanQR,
    Milk, MilkOrder, MilkOrderItem,
    Expense, ExpenseCategory
)

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'user_id', 
            'name', 
            'full_name', 
            'birthday', 
            'work_status', 
            'telegram', 
            'date_start', 
            'experience',
            'type_salary', 
            'rate', 
            'percent', 
            'active_status',
            'max_user_id',
            'avatar'
        ]
        read_only_fields = ['user_id']


class CashierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cashier
        fields = [
            'id', 
            'adress', 
            'status', 
            'created_at', 
            'short_name_point'
        ]


class ShiftSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='user_id.name', read_only=True)
    cashier_name = serializers.CharField(source='cashier_id.short_name_point', read_only=True)
    
    class Meta:
        model = Shift
        fields = [
            'id', 
            'user_id', 
            'employee_name',
            'cashier_id', 
            'cashier_name',
            'date_shift', 
            'active_status'
        ]


class LoyaltyCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyCard
        fields = [
            'id', 
            'full_name', 
            'status', 
            'created_at', 
            'how_find',
            'birthday',
            'bonuses',
            'university_percent',
            'max_id',
            'avatar'
        ]
        read_only_fields = ['id', 'created_at']


class DrinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drink
        fields = [
            'id', 
            'name', 
            'size',
            'url'
        ]


class SyrupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syrup
        fields = [
            'id', 
            'name', 
            'url'
        ]


class CouponSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Coupon
        fields = [
            'id', 
            'tg_id', 
            'drink', 
            'syrup', 
            'created_at', 
            'used', 
            'used_at',
            'max_id'
        ]
        read_only_fields = ['id', 'created_at', 'used_at']


class ReceiptSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='shift_id.user_id.name', read_only=True)
    cashier_name = serializers.CharField(source='cashier_id.short_name_point', read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'id', 
            'shift_id', 
            'employee_name',
            'cashier_id', 
            'cashier_name',
            'loyalty_card_id', 
            'type', 
            'date_operation', 
            'amount', 
            'payment_method', 
            'bonus_add', 
            'bonus_remove'
        ]
        read_only_fields = ['id']

class TimeScanQRSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeScanQR
        fields = ['id', 'loyalty_card_id', 'shift_id', 'cashier_id', 'scan_time', 'bonus_used', 'used_at', 'comment_loyalty_card', 'is_own_cup']

class MilkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milk
        fields = [
            'id', 
            'name_product', 
            'count', 
            'unit'
        ]

class MilkOrderItemSerializer(serializers.ModelSerializer):
    milk = MilkSerializer(read_only=True)

    milk_id = serializers.CharField(
        source='milk',
        write_only=True
    )
    
    class Meta:
        model = MilkOrderItem
        fields = [
            'id',
            'milk',
            'milk_id',
            'quantity'
        ]
    
    def create(self, validated_data):
        milk_name = validated_data.pop('milk')
        try:
            milk_obj = Milk.objects.get(name_product=milk_name)
        except Milk.DoesNotExist:
            raise serializers.ValidationError({
                'milk_id': f'Молоко "{milk_name}" не найдено'
            })
        return MilkOrderItem.objects.create(milk=milk_obj, **validated_data)

class MilkOrderSerializer(serializers.ModelSerializer):
    cashier = serializers.CharField(source='cashier.short_name_point', read_only=True)
    cashier_address = serializers.CharField(source='cashier.adress', read_only=True)
    items = MilkOrderItemSerializer(many=True, read_only=True)
    total_quantity = serializers.ReadOnlyField()
    
    class Meta:
        model = MilkOrder
        fields = [
            'id',
            'cashier',
            'cashier_address',
            'created_at',
            'status',
            'comment',
            'items',
            'total_quantity'
        ]
        read_only_fields = ['id', 'created_at', 'total_quantity']

class MilkOrderCreateSerializer(serializers.ModelSerializer):
    cashier = serializers.CharField(write_only=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    
    class Meta:
        model = MilkOrder
        fields = [
            'id',
            'cashier',
            'cashier_address',
            'status',
            'comment',
            'items',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'status']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')

        cashier_short_name = validated_data.pop('cashier')
        try:
            cashier_obj = Cashier.objects.get(short_name_point=cashier_short_name)
        except Cashier.DoesNotExist:
            raise serializers.ValidationError({
                'cashier': f'Касса "{cashier_short_name}" не найдена'
            })

        order = MilkOrder.objects.create(cashier=cashier_obj, **validated_data)
        
        for item_data in items_data:
            milk_id = item_data.pop('milk_id')
            try:
                milk_obj = Milk.objects.get(id=milk_id)
            except Milk.DoesNotExist:
                raise serializers.ValidationError({
                    'milk_id': f'Молоко "{milk_obj.name_product}" не найдено'
                })

            MilkOrderItem.objects.create(order_id=order, milk=milk_obj, **item_data)
        
        return order
    
class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']

class CashierShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cashier
        fields = ['id', 'short_name_point', 'adress']

class ExpenseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['cashier', 'category', 'amount', 'comment']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        return value

class ExpenseListSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source='cashier.short_name_point', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Expense
        fields = ['id', 'cashier_name', 'category_name', 'amount', 'comment', 'created_at']
