from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from categories.models import Category
from .models import Expense
from .forms import ExpenseForm

class ExpenseModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.category = Category.objects.create(user=self.user, name='Food')

    def test_expense_creation_and_fields(self):
        expense = Expense.objects.create(
            user=self.user,
            name='Lunch',
            amount=Decimal('15.50'),
            date=datetime.date(2026, 6, 3),
            category=self.category,
            description='Lunch at cafe'
        )
        self.assertEqual(expense.name, 'Lunch')
        self.assertEqual(expense.amount, Decimal('15.50'))
        self.assertEqual(expense.category, self.category)
        self.assertEqual(expense.user, self.user)
        self.assertIn('Lunch', str(expense))

    def test_category_on_delete_set_null(self):
        expense = Expense.objects.create(
            user=self.user,
            name='Lunch',
            amount=Decimal('15.50'),
            date=datetime.date(2026, 6, 3),
            category=self.category
        )
        self.assertEqual(expense.category, self.category)
        
        # Delete category and check if expense category is set to Null (SET_NULL)
        self.category.delete()
        expense.refresh_from_db()
        self.assertNull = self.assertIsNone
        self.assertIsNone(expense.category)

class ExpenseFormTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.cat1 = Category.objects.create(user=self.user1, name='User1 Food')
        self.cat2 = Category.objects.create(user=self.user2, name='User2 Rent')

    def test_form_category_queryset_filtering(self):
        # Form for user1 should only include user1's categories
        form1 = ExpenseForm(user=self.user1)
        categories_queryset1 = form1.fields['category'].queryset
        self.assertIn(self.cat1, categories_queryset1)
        self.assertNotIn(self.cat2, categories_queryset1)

        # Form for user2 should only include user2's categories
        form2 = ExpenseForm(user=self.user2)
        categories_queryset2 = form2.fields['category'].queryset
        self.assertNotIn(self.cat1, categories_queryset2)
        self.assertIn(self.cat2, categories_queryset2)

class ExpenseViewsTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.cat1 = Category.objects.create(user=self.user1, name='Food')
        self.expense1 = Expense.objects.create(
            user=self.user1, name='Lunch', amount=Decimal('15.50'), date=datetime.date(2026, 6, 3), category=self.cat1
        )
        self.expense2 = Expense.objects.create(
            user=self.user2, name='Rent', amount=Decimal('1000.00'), date=datetime.date(2026, 6, 1)
        )

    def test_expense_list_login_required(self):
        response = self.client.get(reverse('expense-list'))
        self.assertNotEqual(response.status_code, 200)

    def test_expense_list_user_isolation(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('expense-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lunch')
        self.assertNotContains(response, 'Rent')
        # Total expense check
        self.assertEqual(response.context['total_expense'], Decimal('15.50'))

    def test_expense_create_post(self):
        self.client.force_login(self.user1)
        from accounts.models import Account
        account, _ = Account.objects.get_or_create(user=self.user1, name='Cash', account_type='Cash')
        
        response = self.client.post(reverse('transaction-add'), {
            'type': 'expense',
            'date': '2026-06-03',
            'account': account.id,
            'rows': [{
                'name': 'Groceries',
                'amount': '45.20',
                'category': self.cat1.id,
                'description': 'Weekly supply'
            }]
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertTrue(Expense.objects.filter(user=self.user1, name='Groceries').exists())

    def test_expense_update_owner(self):
        self.client.force_login(self.user1)
        from accounts.models import Account
        account, _ = Account.objects.get_or_create(user=self.user1, name='Cash', account_type='Cash')
        
        response = self.client.post(reverse('expense-edit', kwargs={'pk': self.expense1.pk}), {
            'account': account.id,
            'name': 'Updated Lunch',
            'amount': '18.00',
            'date': '2026-06-03',
            'category': self.cat1.id,
            'description': 'Updated'
        })
        self.assertEqual(response.status_code, 302)
        self.expense1.refresh_from_db()
        self.assertEqual(self.expense1.name, 'Updated Lunch')
        self.assertEqual(self.expense1.amount, Decimal('18.00'))

    def test_expense_update_non_owner(self):
        self.client.force_login(self.user2)
        response = self.client.post(reverse('expense-edit', kwargs={'pk': self.expense1.pk}), {
            'name': 'Hacked',
            'amount': '10.00',
            'date': '2026-06-03'
        })
        self.assertEqual(response.status_code, 404)

    def test_expense_delete_owner(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse('expense-delete', kwargs={'pk': self.expense1.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expense.objects.filter(pk=self.expense1.pk).exists())

    def test_expense_delete_non_owner(self):
        self.client.force_login(self.user2)
        response = self.client.post(reverse('expense-delete', kwargs={'pk': self.expense1.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Expense.objects.filter(pk=self.expense1.pk).exists())
