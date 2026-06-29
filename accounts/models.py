from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('Cash', 'Cash'),
        ('Bank Account', 'Bank Account'),
        ('Wallet', 'Wallet'),
        ('Credit Card', 'Credit Card'),
        ('UPI', 'UPI'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    minimum_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True)
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('CLOSED', 'Closed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.account_type})"

    def invalidate_cache(self):
        for attr in ['_current_balance_cache', '_settings_cache', '_total_income', '_total_expense']:
            if hasattr(self, attr):
                delattr(self, attr)

    @property
    def current_balance(self):
        if hasattr(self, '_current_balance_cache'):
            return self._current_balance_cache

        if hasattr(self, '_total_income'):
            self._current_balance_cache = (
                Decimal(str(self.initial_balance)) + 
                Decimal(str(self._total_income)) - 
                Decimal(str(self._total_expense))
            )
            return self._current_balance_cache

        total_income = self.incomes.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        total_expense = self.expenses.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        self._current_balance_cache = (
            Decimal(str(self.initial_balance)) + 
            Decimal(str(total_income)) - 
            Decimal(str(total_expense))
        )
        return self._current_balance_cache

    @property
    def bootstrap_icon(self):
        mapping = {
            'Cash': 'bi-cash-coin',
            'Bank Account': 'bi-bank',
            'Wallet': 'bi-wallet2',
            'Credit Card': 'bi-credit-card',
            'UPI': 'bi-qr-code',
        }
        return mapping.get(self.account_type, 'bi-wallet2')

    @property
    def theme_color_class(self):
        mapping = {
            'Cash': 'color-1',
            'Bank Account': 'color-2',
            'Wallet': 'color-2',
            'Credit Card': 'color-3',
            'UPI': 'color-1',
        }
        return mapping.get(self.account_type, 'color-2')

    @property
    def effective_minimum_balance(self):
        """Returns the actual threshold balance being used for alerts (either own minimum_balance or fallback default)."""
        threshold = self.minimum_balance
        if not threshold or threshold <= 0:
            threshold = Decimal('0.00')
        return threshold

    @property
    def is_below_minimum(self):
        """Returns True if current balance is at or below the minimum balance threshold."""
        if self.status == 'CLOSED':
            return False

        threshold = self.effective_minimum_balance
        if threshold and threshold > 0:
            return self.current_balance <= threshold
        return False

    @property
    def shortage(self):
        """Returns the shortage amount if the balance is at or below the minimum."""
        threshold = self.effective_minimum_balance
        if threshold and threshold > 0 and self.current_balance <= threshold:
            return threshold - self.current_balance
        return Decimal('0.00')

    @property
    def coverage_percentage(self):
        """Returns the current balance as a percentage of the minimum balance."""
        threshold = self.effective_minimum_balance
        if threshold and threshold > 0:
            pct = (self.current_balance / threshold) * 100
            return max(0.0, float(pct))
        return 100.0


    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError

        if self.minimum_balance is not None and self.minimum_balance < 0:
            raise ValidationError({'minimum_balance': "Low balance threshold cannot be negative."})

        if self.minimum_balance is not None and self.minimum_balance > self.initial_balance:
            raise ValidationError({'minimum_balance': "Low balance threshold cannot be greater than the opening balance."})

        if self.pk:
            try:
                old_instance = Account.objects.get(pk=self.pk)
                if old_instance.minimum_balance != self.minimum_balance:
                    if not getattr(self, '_explicit_threshold_edit', False):
                        raise ValidationError({'minimum_balance': "Threshold values can only be changed when explicitly edited by the user."})
            except Account.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        self.invalidate_cache()
        self.full_clean()
        super().save(*args, **kwargs)

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)
        self.invalidate_cache()





class UserSettings(models.Model):
    CURRENCY_CHOICES = [
        ('₹', 'INR (₹)'),
        ('$', 'USD ($)'),
        ('€', 'EUR (€)'),
        ('£', 'GBP (£)'),
        ('¥', 'JPY (¥)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹')

    def __str__(self):
        return f"{self.user.username}'s settings"


def annotate_balance(queryset):
    from django.db.models import Subquery, Sum, OuterRef, DecimalField
    from django.db.models.functions import Coalesce
    from income.models import Income
    from expenses.models import Expense
    
    incomes_sub = Income.objects.filter(account=OuterRef('pk')).values('account').annotate(total=Sum('amount')).values('total')
    expenses_sub = Expense.objects.filter(account=OuterRef('pk')).values('account').annotate(total=Sum('amount')).values('total')
    
    return queryset.annotate(
        _total_income=Coalesce(Subquery(incomes_sub), Decimal('0.00'), output_field=DecimalField()),
        _total_expense=Coalesce(Subquery(expenses_sub), Decimal('0.00'), output_field=DecimalField()),
    )
