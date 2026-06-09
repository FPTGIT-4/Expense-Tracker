import sys
import os
# Add parent directory to sys.path so config and other app modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Account, AccountTransfer
from income.models import Income
from expenses.models import Expense
from transactions.models import TransactionHistory
from django.utils import timezone

def backfill():
    # Clear existing history first to avoid duplicates
    TransactionHistory.objects.all().delete()
    print("Cleared existing transaction history.")

    for user in User.objects.all():
        print(f"Processing history for user: {user.username}")
        for account in Account.objects.filter(user=user):
            # Gather all events for this account
            timeline = []

            # 1. Account Creation (virtual event)
            timeline.append({
                'type': 'CREATION',
                'date': account.created_at.date() if account.created_at else timezone.localdate(),
                'timestamp': account.created_at if account.created_at else timezone.now(),
                'amount': account.initial_balance,
                'obj': account,
                'category_name': 'Account Creation',
                'description': f"Account '{account.name}' created with initial balance."
            })

            # 2. Incomes
            for inc in Income.objects.filter(account=account):
                timestamp = inc.created_at if inc.created_at else timezone.now()
                timeline.append({
                    'type': 'INCOME',
                    'date': inc.date,
                    'timestamp': timestamp,
                    'amount': inc.amount,
                    'obj': inc,
                    'category_name': inc.source,
                    'description': inc.description
                })

            # 3. Expenses
            for exp in Expense.objects.filter(account=account):
                timestamp = exp.created_at if exp.created_at else timezone.now()
                cat_name = exp.category.name if exp.category else 'Uncategorized'
                timeline.append({
                    'type': 'EXPENSE',
                    'date': exp.date,
                    'timestamp': timestamp,
                    'amount': exp.amount,
                    'obj': exp,
                    'category_name': cat_name,
                    'description': exp.description
                })

            # 4. Outgoing Transfers
            for tr in AccountTransfer.objects.filter(from_account=account):
                timestamp = tr.created_at if tr.created_at else timezone.now()
                timeline.append({
                    'type': 'TRANSFER_OUT',
                    'date': tr.transfer_date,
                    'timestamp': timestamp,
                    'amount': tr.amount,
                    'obj': tr,
                    'category_name': 'Transfer Out',
                    'description': tr.note
                })

            # 5. Incoming Transfers
            for tr in AccountTransfer.objects.filter(to_account=account):
                timestamp = tr.created_at if tr.created_at else timezone.now()
                timeline.append({
                    'type': 'TRANSFER_IN',
                    'date': tr.transfer_date,
                    'timestamp': timestamp,
                    'amount': tr.amount,
                    'obj': tr,
                    'category_name': 'Transfer In',
                    'description': tr.note
                })

            # Sort timeline by date, then by timestamp/created_at
            timeline.sort(key=lambda x: (x['date'], x['timestamp']))

            # Compute running balance
            running_balance = Decimal('0.00')

            for event in timeline:
                e_type = event['type']
                amt = event['amount']

                if e_type == 'CREATION':
                    balance_before = Decimal('0.00')
                    running_balance = amt
                    balance_after = running_balance
                elif e_type == 'INCOME':
                    balance_before = running_balance
                    running_balance += amt
                    balance_after = running_balance
                elif e_type == 'EXPENSE':
                    balance_before = running_balance
                    running_balance -= amt
                    balance_after = running_balance
                elif e_type == 'TRANSFER_OUT':
                    balance_before = running_balance
                    running_balance -= amt
                    balance_after = running_balance
                elif e_type == 'TRANSFER_IN':
                    balance_before = running_balance
                    running_balance += amt
                    balance_after = running_balance
                else:
                    balance_before = running_balance
                    balance_after = running_balance

                # Save history record
                history = TransactionHistory(
                    user=user,
                    activity_type=e_type,
                    account=account,
                    amount=amt,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    category_name=event['category_name'],
                    description=event['description'],
                    date=event['date'],
                    timestamp=event['timestamp']
                )

                # Link objects
                if e_type == 'INCOME':
                    history.income = event['obj']
                elif e_type == 'EXPENSE':
                    history.expense = event['obj']
                elif e_type == 'TRANSFER_OUT' or e_type == 'TRANSFER_IN':
                    history.transfer = event['obj']
                    # Keep to_account reference
                    if e_type == 'TRANSFER_OUT':
                        history.to_account = event['obj'].to_account
                    else:
                        history.to_account = event['obj'].from_account

                history.save()

            print(f"  Account '{account.name}': processed {len(timeline)} events. Final running balance: {running_balance}")

if __name__ == '__main__':
    backfill()
