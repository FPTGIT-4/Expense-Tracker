from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from income.models import Income
from expenses.models import Expense
from accounts.models import Account, AccountTransfer
from .models import TransactionHistory

@receiver(post_save, sender=Income)
def save_income_history(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    instance.account.invalidate_cache()
    amount = Decimal(str(instance.amount))
    balance_after = instance.account.current_balance
    balance_before = balance_after - amount

    if created:
        TransactionHistory.objects.create(
            user=instance.user,
            activity_type='INCOME',
            account=instance.account,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            category_name=instance.source,
            description=instance.description,
            date=instance.date,
            income=instance
        )
    else:
        TransactionHistory.objects.filter(income=instance).update(
            account=instance.account,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            category_name=instance.source,
            description=instance.description,
            date=instance.date
        )

@receiver(post_save, sender=Expense)
def save_expense_history(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    instance.account.invalidate_cache()
    amount = Decimal(str(instance.amount))
    balance_after = instance.account.current_balance
    balance_before = balance_after + amount
    cat_name = instance.category.name if instance.category else 'Uncategorized'

    if created:
        TransactionHistory.objects.create(
            user=instance.user,
            activity_type='EXPENSE',
            account=instance.account,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            category_name=cat_name,
            description=instance.description,
            date=instance.date,
            expense=instance
        )
    else:
        TransactionHistory.objects.filter(expense=instance).update(
            account=instance.account,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            category_name=cat_name,
            description=instance.description,
            date=instance.date
        )

@receiver(post_save, sender=AccountTransfer)
def save_transfer_history(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    instance.from_account.invalidate_cache()
    instance.to_account.invalidate_cache()
    amount = Decimal(str(instance.amount))
    from_after = instance.from_account.current_balance
    from_before = from_after + amount

    to_after = instance.to_account.current_balance
    to_before = to_after - amount

    if created:
        TransactionHistory.objects.create(
            user=instance.user,
            activity_type='TRANSFER_OUT',
            account=instance.from_account,
            to_account=instance.to_account,
            amount=amount,
            balance_before=from_before,
            balance_after=from_after,
            category_name='Transfer Out',
            description=instance.note,
            date=instance.transfer_date,
            transfer=instance
        )
        TransactionHistory.objects.create(
            user=instance.user,
            activity_type='TRANSFER_IN',
            account=instance.to_account,
            to_account=instance.from_account,
            amount=amount,
            balance_before=to_before,
            balance_after=to_after,
            category_name='Transfer In',
            description=instance.note,
            date=instance.transfer_date,
            transfer=instance
        )
    else:
        TransactionHistory.objects.filter(transfer=instance, activity_type='TRANSFER_OUT').update(
            account=instance.from_account,
            to_account=instance.to_account,
            amount=amount,
            balance_before=from_before,
            balance_after=from_after,
            description=instance.note,
            date=instance.transfer_date
        )
        TransactionHistory.objects.filter(transfer=instance, activity_type='TRANSFER_IN').update(
            account=instance.to_account,
            to_account=instance.from_account,
            amount=amount,
            balance_before=to_before,
            balance_after=to_after,
            description=instance.note,
            date=instance.transfer_date
        )

@receiver(pre_save, sender=Account)
def pre_save_account(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    if instance.pk:
        try:
            old_instance = Account.objects.get(pk=instance.pk)
            instance._old_initial_balance = old_instance.initial_balance
        except Account.DoesNotExist:
            instance._old_initial_balance = None
    else:
        instance._old_initial_balance = None

@receiver(post_save, sender=Account)
def save_account_history(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if created:
        TransactionHistory.objects.create(
            user=instance.user,
            activity_type='CREATION',
            account=instance,
            amount=instance.initial_balance,
            balance_before=Decimal('0.00'),
            balance_after=instance.initial_balance,
            category_name='Account Creation',
            description=f"Account '{instance.name}' created with initial balance.",
            date=timezone.localdate()
        )
    else:
        old_init = getattr(instance, '_old_initial_balance', None)
        if old_init is not None and old_init != instance.initial_balance:
            diff = instance.initial_balance - old_init
            TransactionHistory.objects.create(
                user=instance.user,
                activity_type='ADJUSTMENT',
                account=instance,
                amount=diff,
                balance_after=instance.current_balance,
                balance_before=instance.current_balance - diff,
                category_name='Balance Adjustment',
                description=f"Initial balance changed from {old_init} to {instance.initial_balance}.",
                date=timezone.localdate()
            )

@receiver(post_delete, sender=Income)
def delete_income_history(sender, instance, **kwargs):
    if hasattr(instance, 'account') and instance.account:
        instance.account.invalidate_cache()

@receiver(post_delete, sender=Expense)
def delete_expense_history(sender, instance, **kwargs):
    if hasattr(instance, 'account') and instance.account:
        instance.account.invalidate_cache()

@receiver(post_delete, sender=AccountTransfer)
def delete_transfer_history(sender, instance, **kwargs):
    if hasattr(instance, 'from_account') and instance.from_account:
        instance.from_account.invalidate_cache()
    if hasattr(instance, 'to_account') and instance.to_account:
        instance.to_account.invalidate_cache()
