from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from categories.models import Category

class CompanyAccount(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_accounts')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    @property
    def total_income(self):
        return self.incomes.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def total_expenses(self):
        return self.expenses.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def current_balance(self):
        return self.opening_balance + self.total_income - self.total_expenses


class CompanyIncome(models.Model):
    company_account = models.ForeignKey(CompanyAccount, on_delete=models.CASCADE, related_name='incomes')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(max_length=100)
    date = models.DateField(default=timezone.localdate)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Income: {self.source} ({self.amount}) for {self.company_account.name}"


class CompanyExpense(models.Model):
    company_account = models.ForeignKey(CompanyAccount, on_delete=models.CASCADE, related_name='expenses')
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='company_expenses')
    date = models.DateField(default=timezone.localdate)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Expense: {self.name} ({self.amount}) for {self.company_account.name}"
