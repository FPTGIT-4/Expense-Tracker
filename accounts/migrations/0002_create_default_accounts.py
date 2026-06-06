from django.db import migrations
from decimal import Decimal

def create_default_accounts_and_migrate_txs(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Account = apps.get_model('accounts', 'Account')
    Income = apps.get_model('income', 'Income')
    Expense = apps.get_model('expenses', 'Expense')

    for user in User.objects.all():
        # Only create a default Cash account if the user does not have any accounts
        account, created = Account.objects.get_or_create(
            user=user,
            account_type='Cash',
            defaults={
                'name': 'Cash',
                'initial_balance': Decimal('0.00')
            }
        )
        
        # Link all incomes for this user that don't have an account yet
        Income.objects.filter(user=user, account__isnull=True).update(account=account)
        
        # Link all expenses for this user that don't have an account yet
        Expense.objects.filter(user=user, account__isnull=True).update(account=account)

def reverse_default_accounts(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('income', '0002_income_account'),
        ('expenses', '0002_expense_account'),
    ]

    operations = [
        migrations.RunPython(create_default_accounts_and_migrate_txs, reverse_default_accounts),
    ]
