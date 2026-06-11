from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class Debt(models.Model):
    DEBT_TYPE_CHOICES = [
        ('Borrowed', 'Money I Owe (Borrowed)'),
        ('Lent', 'Money Owed to Me (Lent)'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Settled', 'Settled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='debts')
    person_name = models.CharField(max_length=100)
    debt_type = models.CharField(max_length=15, choices=DEBT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'person_name']

    def __str__(self):
        return f"{self.person_name} ({self.debt_type}) - {self.amount}"

    @property
    def total_paid(self):
        return self.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def remaining_balance(self):
        remaining = self.amount - self.total_paid
        return max(Decimal('0.00'), remaining)

    @property
    def repayment_percentage(self):
        if self.amount <= 0:
            return 0
        pct = (self.total_paid / self.amount) * 100
        return min(100, int(pct))

    @property
    def is_overdue(self):
        if self.status == 'Settled':
            return False
        if self.due_date:
            return self.due_date < timezone.localdate()
        return False

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': "Debt amount must be a positive number greater than zero."})
        if self.date and self.due_date and self.due_date < self.date:
            raise ValidationError({'due_date': "Due date cannot be before the debt creation date."})

    def update_status(self):
        # Recalculate status based on payments
        if self.remaining_balance <= 0:
            self.status = 'Settled'
        else:
            self.status = 'Active'
        super().save(update_fields=['status'])

    def save(self, *args, **kwargs):
        self.full_clean()
        # Auto update status if self.pk exists
        if self.pk:
            if self.remaining_balance <= 0:
                self.status = 'Settled'
        super().save(*args, **kwargs)


class Repayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Repayment of {self.amount} on {self.date}"

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': "Repayment amount must be a positive number greater than zero."})
        
        # Check that payment doesn't exceed remaining amount (excluding self if already saved)
        if self.amount is not None and self.debt_id:
            # Calculate total paid by other repayments
            other_payments = self.debt.payments.exclude(pk=self.pk)
            total_other_paid = other_payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            remaining = self.debt.amount - total_other_paid
            if self.amount > remaining:
                raise ValidationError({'amount': f"Repayment amount ({self.amount}) cannot exceed the remaining balance ({remaining})."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.debt.update_status()

    def delete(self, *args, **kwargs):
        debt = self.debt
        super().delete(*args, **kwargs)
        debt.update_status()
