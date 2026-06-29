from django.db import models
from django.contrib.auth.models import User
from categories.models import Category


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='incomes', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incomes',
        limit_choices_to={'category_type': 'income'},
    )
    # source kept nullable for backward-compat with older records
    source = models.CharField(max_length=50, blank=True, null=True)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
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
        label = self.category.name if self.category else (self.source or 'Income')
        return f"{self.user.username} - {label} (${self.amount}) on {self.date}"
