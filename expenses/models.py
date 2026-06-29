from django.db import models
from django.contrib.auth.models import User
from categories.models import Category, SubCategory

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    account = models.ForeignKey('accounts.Account', on_delete=models.SET_NULL, related_name='expenses', null=True, blank=True)  # Preserve expenses when account is deleted
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.account_id:
            from accounts.models import Account
            from decimal import Decimal
            account, _ = Account.objects.get_or_create(
                user=self.user,
                account_type='Cash',
                defaults={'name': 'Cash', 'initial_balance': Decimal('0.00')}
            )
            self.account = account
        super().save(*args, **kwargs)
        if self.account:
            self.account.invalidate_cache()

    def delete(self, *args, **kwargs):
        account = self.account
        super().delete(*args, **kwargs)
        if account:
            account.invalidate_cache()

    def __str__(self):
        return f"{self.user.username} - {self.name} (${self.amount}) on {self.date}"
