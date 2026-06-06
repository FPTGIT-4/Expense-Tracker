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

    @property
    def current_balance(self):
        total_income = self.incomes.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        total_expense = self.expenses.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        outgoing_transfers = self.outgoing_transfers.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        incoming_transfers = self.incoming_transfers.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        return self.initial_balance + total_income - total_expense + incoming_transfers - outgoing_transfers

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
    def is_below_minimum(self):
        """Returns True if current balance is below the minimum balance threshold."""
        if self.minimum_balance and self.minimum_balance > 0:
            return self.current_balance < self.minimum_balance
        return False


from django.utils import timezone
from django.core.exceptions import ValidationError

class AccountTransfer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers')
    from_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='incoming_transfers')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transfer_date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transfer_date', '-created_at']

    def __str__(self):
        return f"Transfer of ₹{self.amount} from {self.from_account} to {self.to_account}"

    def clean(self):
        super().clean()
        if self.from_account == self.to_account:
            raise ValidationError("Source and destination accounts cannot be the same.")
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': "Transfer amount must be a positive number."})

        if self.from_account:
            if self.from_account.status == 'INACTIVE':
                raise ValidationError({'from_account': "Cannot transfer from an inactive account."})
            elif self.from_account.status == 'CLOSED':
                raise ValidationError({'from_account': "Cannot transfer from a closed account."})

        if self.to_account:
            if self.to_account.status == 'INACTIVE':
                raise ValidationError({'to_account': "Cannot transfer to an inactive account."})
            elif self.to_account.status == 'CLOSED':
                raise ValidationError({'to_account': "Cannot receive transfers into a closed account."})
