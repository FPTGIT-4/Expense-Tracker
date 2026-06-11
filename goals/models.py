from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    target_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['target_date', 'name']

    def __str__(self):
        return f"{self.name} - Goal of {self.target_amount}"

    @property
    def progress_percentage(self):
        if self.target_amount <= 0:
            return 0.0
        pct = (self.current_amount / self.target_amount) * 100
        return min(100.0, float(round(pct, 1)))

    @property
    def remaining_amount(self):
        remaining = self.target_amount - self.current_amount
        return max(Decimal('0.00'), remaining)

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount

    def clean(self):
        super().clean()
        if self.target_amount is not None and self.target_amount <= 0:
            raise ValidationError({'target_amount': "Target amount must be a positive number greater than zero."})
        if self.current_amount is not None and self.current_amount < 0:
            raise ValidationError({'current_amount': "Saved amount cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
