from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TransactionHistory(models.Model):
    ACTIVITY_CHOICES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('ADJUSTMENT', 'Balance Adjustment'),
        ('CREATION', 'Account Creation'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_histories')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='transaction_histories')
    to_account = models.ForeignKey('accounts.Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction_histories_to')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    category_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.localdate)
    timestamp = models.DateTimeField(default=timezone.now)

    # Optional references to original objects
    income = models.ForeignKey('income.Income', on_delete=models.CASCADE, null=True, blank=True)
    expense = models.ForeignKey('expenses.Expense', on_delete=models.CASCADE, null=True, blank=True)
    transfer = models.ForeignKey('accounts.AccountTransfer', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-timestamp']
        verbose_name_plural = "Transaction Histories"

    def __str__(self):
        return f"{self.activity_type} - {self.amount} ({self.date})"

    @property
    def title(self):
        if self.activity_type == 'EXPENSE' and self.expense:
            return self.expense.name
        return self.category_name
