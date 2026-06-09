from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
import datetime

from accounts.models import Account, AccountTransfer
from income.models import Income
from expenses.models import Expense
from categories.models import Category
from transactions.models import TransactionHistory

class TransactionHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='historyuser',
            password='password123',
            email='history@example.com'
        )
        self.client.force_login(self.user)
        
        # Create categories
        self.food_category = Category.objects.create(user=self.user, name='Food')
        
        # Create accounts (this will automatically trigger CREATION history log)
        self.cash_account = Account.objects.create(
            user=self.user,
            name='Cash',
            account_type='Cash',
            initial_balance=Decimal('1000.00')
        )
        self.bank_account = Account.objects.create(
            user=self.user,
            name='Bank',
            account_type='Bank Account',
            initial_balance=Decimal('500.00')
        )

    def test_account_creation_history(self):
        # Verify that two CREATION history logs were created during setUp
        histories = TransactionHistory.objects.filter(activity_type='CREATION')
        self.assertEqual(histories.count(), 2)
        
        cash_history = histories.get(account=self.cash_account)
        self.assertEqual(cash_history.amount, Decimal('1000.00'))
        self.assertEqual(cash_history.balance_before, Decimal('0.00'))
        self.assertEqual(cash_history.balance_after, Decimal('1000.00'))

    def test_income_creation_and_modification_history(self):
        # Create Income
        income = Income.objects.create(
            user=self.user,
            account=self.cash_account,
            amount=Decimal('200.00'),
            source='Salary',
            date=timezone.localdate()
        )
        
        # Verify history log created
        history = TransactionHistory.objects.get(income=income)
        self.assertEqual(history.activity_type, 'INCOME')
        self.assertEqual(history.amount, Decimal('200.00'))
        # Cash account initial balance was 1000, +200 income = 1200
        self.assertEqual(history.balance_before, Decimal('1000.00'))
        self.assertEqual(history.balance_after, Decimal('1200.00'))
        self.assertEqual(history.category_name, 'Salary')

        # Modify Income
        income.amount = Decimal('300.00')
        income.save()

        # Verify history log updated
        history.refresh_from_db()
        self.assertEqual(history.amount, Decimal('300.00'))
        # Cash balance is now 1300
        self.assertEqual(history.balance_before, Decimal('1000.00'))
        self.assertEqual(history.balance_after, Decimal('1300.00'))

        income_id = income.pk
        # Delete Income
        income.delete()
        
        # Verify history log deleted (cascaded)
        self.assertFalse(TransactionHistory.objects.filter(income_id=income_id).exists())

    def test_expense_history(self):
        # Create Expense
        expense = Expense.objects.create(
            user=self.user,
            account=self.cash_account,
            name='Groceries',
            amount=Decimal('150.00'),
            category=self.food_category,
            date=timezone.localdate()
        )
        
        # Verify history
        history = TransactionHistory.objects.get(expense=expense)
        self.assertEqual(history.activity_type, 'EXPENSE')
        self.assertEqual(history.amount, Decimal('150.00'))
        # Cash balance: 1000 - 150 = 850
        self.assertEqual(history.balance_before, Decimal('1000.00'))
        self.assertEqual(history.balance_after, Decimal('850.00'))
        self.assertEqual(history.category_name, 'Food')

    def test_transfer_history(self):
        # Create Account Transfer from Cash (1000) to Bank (500)
        transfer = AccountTransfer.objects.create(
            user=self.user,
            from_account=self.cash_account,
            to_account=self.bank_account,
            amount=Decimal('300.00'),
            transfer_date=timezone.localdate()
        )

        # Verify TRANSFER_OUT history record for Cash
        out_history = TransactionHistory.objects.get(transfer=transfer, activity_type='TRANSFER_OUT')
        self.assertEqual(out_history.account, self.cash_account)
        self.assertEqual(out_history.to_account, self.bank_account)
        # Cash balance: 1000 - 300 = 700
        self.assertEqual(out_history.balance_before, Decimal('1000.00'))
        self.assertEqual(out_history.balance_after, Decimal('700.00'))

        # Verify TRANSFER_IN history record for Bank
        in_history = TransactionHistory.objects.get(transfer=transfer, activity_type='TRANSFER_IN')
        self.assertEqual(in_history.account, self.bank_account)
        self.assertEqual(in_history.to_account, self.cash_account)
        # Bank balance: 500 + 300 = 800
        self.assertEqual(in_history.balance_before, Decimal('500.00'))
        self.assertEqual(in_history.balance_after, Decimal('800.00'))

    def test_balance_adjustment_history(self):
        # Edit initial balance of Cash account
        self.cash_account.initial_balance = Decimal('1500.00')
        self.cash_account.save()

        # Verify adjustment history created
        adjustment = TransactionHistory.objects.get(activity_type='ADJUSTMENT')
        self.assertEqual(adjustment.amount, Decimal('500.00'))
        self.assertEqual(adjustment.balance_before, Decimal('1000.00'))
        self.assertEqual(adjustment.balance_after, Decimal('1500.00'))

    def test_history_list_view_filters_and_search(self):
        # Create some test logs
        income = Income.objects.create(
            user=self.user,
            account=self.cash_account,
            amount=Decimal('100.00'),
            source='Gift',
            date=timezone.localdate()
        )
        expense = Expense.objects.create(
            user=self.user,
            account=self.cash_account,
            name='Movie',
            amount=Decimal('200.00'),
            category=self.food_category,
            date=timezone.localdate()
        )

        response = self.client.get(reverse('transaction-history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_history.html')
        
        # Test Search Filter
        response = self.client.get(reverse('transaction-history'), {'q': 'Gift'})
        self.assertEqual(response.status_code, 200)
        history_list = list(response.context['history_list'])
        self.assertTrue(any(item.activity_type == 'INCOME' and item.category_name == 'Gift' for item in history_list))
        self.assertFalse(any(item.activity_type == 'EXPENSE' and item.expense and item.expense.name == 'Movie' for item in history_list))

        # Test Account Filter
        response = self.client.get(reverse('transaction-history'), {'account': self.cash_account.pk})
        self.assertEqual(response.status_code, 200)
        
        # Test Type Filter
        response = self.client.get(reverse('transaction-history'), {'type': 'EXPENSE'})
        self.assertEqual(response.status_code, 200)
        history_list = list(response.context['history_list'])
        self.assertTrue(any(item.activity_type == 'EXPENSE' and item.expense and item.expense.name == 'Movie' for item in history_list))
        self.assertFalse(any(item.activity_type == 'INCOME' and item.category_name == 'Gift' for item in history_list))
