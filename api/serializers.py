from rest_framework import serializers
from django.contrib.auth.models import User
from accounts.models import Account, AccountTransfer, UserSettings
from categories.models import Category
from income.models import Income
from expenses.models import Expense
from budgets.models import Budget
from decimal import Decimal

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            'id', 'currency', 'budget_threshold', 'enable_budget_alerts',
            'low_balance_alerts', 'low_balance_show_navbar_badge',
            'low_balance_show_dashboard_banner', 'low_balance_show_dashboard_panel',
            'low_balance_alert_scope', 'low_balance_default_minimum', 'dark_mode'
        ]
        read_only_fields = ['id']

class UserSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'settings']
        read_only_fields = ['id']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['username', 'password', 'confirm_password', 'email', 'first_name', 'last_name']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )
        # Create default UserSettings and default Account (Cash)
        UserSettings.objects.get_or_create(user=user)
        Account.objects.get_or_create(
            user=user,
            account_type='Cash',
            defaults={'name': 'Cash', 'initial_balance': Decimal('0.00')}
        )
        return user

class AccountSerializer(serializers.ModelSerializer):
    current_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    effective_minimum_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_below_minimum = serializers.BooleanField(read_only=True)
    shortage = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    coverage_percentage = serializers.FloatField(read_only=True)
    bootstrap_icon = serializers.CharField(read_only=True)
    theme_color_class = serializers.CharField(read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'initial_balance', 'minimum_balance',
            'status', 'notes', 'created_at', 'updated_at', 'current_balance',
            'effective_minimum_balance', 'is_below_minimum', 'shortage',
            'coverage_percentage', 'bootstrap_icon', 'theme_color_class'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_minimum_balance(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Low balance threshold cannot be negative.")
        return value

    def validate(self, attrs):
        # We need to access initial_balance. When updating, it might not be in attrs
        initial_balance = attrs.get('initial_balance', self.instance.initial_balance if self.instance else Decimal('0.00'))
        minimum_balance = attrs.get('minimum_balance', self.instance.minimum_balance if self.instance else Decimal('0.00'))
        
        if minimum_balance > initial_balance:
            raise serializers.ValidationError({"minimum_balance": "Low balance threshold cannot be greater than the opening balance."})
        
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Mark as explicit edit for model-level validations
        account = Account(**validated_data)
        account._explicit_threshold_edit = True
        account.save()
        return account

    def update(self, instance, validated_data):
        # Allow minimum_balance threshold change when explicitly edited by user via API
        instance._explicit_threshold_edit = True
        return super().update(instance, validated_data)

class AccountTransferSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.name', read_only=True)

    class Meta:
        model = AccountTransfer
        fields = [
            'id', 'from_account', 'from_account_name', 'to_account', 'to_account_name',
            'amount', 'transfer_date', 'note', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        from_account = attrs['from_account']
        to_account = attrs['to_account']
        amount = attrs['amount']

        if from_account == to_account:
            raise serializers.ValidationError("Source and destination accounts cannot be the same.")
        
        if amount <= 0:
            raise serializers.ValidationError({"amount": "Transfer amount must be a positive number."})

        # Ensure user owns both accounts
        user = self.context['request'].user
        if from_account.user != user or to_account.user != user:
            raise serializers.ValidationError("You do not own one or both of these accounts.")

        if from_account.status in ['INACTIVE', 'CLOSED']:
            raise serializers.ValidationError({"from_account": f"Cannot transfer from a {from_account.status.lower()} account."})
        
        if to_account.status in ['INACTIVE', 'CLOSED']:
            raise serializers.ValidationError({"to_account": f"Cannot transfer to a {to_account.status.lower()} account."})

        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class IncomeSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = Income
        fields = [
            'id', 'account', 'account_name', 'amount', 'source', 'date',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_account(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("Account does not belong to this user.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ExpenseSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'account', 'account_name', 'name', 'amount', 'date',
            'description', 'category', 'category_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_account(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("Account does not belong to this user.")
        return value

    def validate_category(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("Category does not belong to this user.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_budget = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    usage_percentage = serializers.FloatField(read_only=True)
    status_text = serializers.CharField(read_only=True)
    status_class = serializers.CharField(read_only=True)

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'category_name', 'budget_amount', 'month', 'year',
            'notes', 'is_active', 'created_at', 'updated_at', 'total_spent',
            'remaining_budget', 'usage_percentage', 'status_text', 'status_class'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_category(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("Category does not belong to this user.")
        return value

    def validate(self, attrs):
        category = attrs.get('category', self.instance.category if self.instance else None)
        month = attrs.get('month', self.instance.month if self.instance else None)
        year = attrs.get('year', self.instance.year if self.instance else None)

        if category and month and year:
            qs = Budget.objects.filter(category=category, month=month, year=year)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A budget for this category and month/year already exists.")
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
