from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('Cash', 'Cash'),
        ('Bank Account', 'Bank Account'),
        ('GPay', 'GPay'),
        ('PhonePe', 'PhonePe'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Other Wallets', 'Other Wallets'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.account_type})"

    @property
    def current_balance(self):
        total_income = self.incomes.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        total_expense = self.expenses.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        return self.initial_balance + total_income - total_expense
