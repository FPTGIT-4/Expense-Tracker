from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime

from categories.models import Category
from .models import CompanyAccount, CompanyIncome, CompanyExpense

class CompanyModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='businessuser', password='password123')
        self.company = CompanyAccount.objects.create(
            user=self.user,
            name='Acme Corp',
            description='Test company description',
            opening_balance=Decimal('5000.00'),
            status='ACTIVE'
        )

    def test_company_balance_calculation(self):
        # Initial balance should equal opening balance
        self.assertEqual(self.company.current_balance, Decimal('5000.00'))

        # Add Income
        CompanyIncome.objects.create(
            company_account=self.company,
            amount=Decimal('1500.50'),
            source='Client Payment',
            date=datetime.date(2026, 6, 1)
        )
        self.assertEqual(self.company.current_balance, Decimal('6500.50'))

        # Add Expense
        category = Category.objects.create(user=self.user, name='Office Supplies')
        CompanyExpense.objects.create(
            company_account=self.company,
            name='Laptops',
            amount=Decimal('2000.00'),
            category=category,
            date=datetime.date(2026, 6, 2)
        )
        self.assertEqual(self.company.current_balance, Decimal('4500.50'))


class CompanyCRUDViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.company = CompanyAccount.objects.create(
            user=self.user,
            name='Beta LLC',
            opening_balance=Decimal('1000.00'),
            status='ACTIVE'
        )
        self.other_company = CompanyAccount.objects.create(
            user=self.other_user,
            name='Gamma Inc',
            opening_balance=Decimal('2000.00'),
            status='ACTIVE'
        )

    def test_company_list_view(self):
        # Redirect anonymous
        response = self.client.get(reverse('company-account-list'))
        self.assertEqual(response.status_code, 302)

        # Logged in
        self.client.force_login(self.user)
        response = self.client.get(reverse('company-account-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Beta LLC')
        self.assertNotContains(response, 'Gamma Inc')

    def test_company_detail_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('company-account-detail', args=[self.company.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Beta LLC')

        # Accessing other user's company account returns 404
        response = self.client.get(reverse('company-account-detail', args=[self.other_company.pk]))
        self.assertEqual(response.status_code, 404)

    def test_company_create_view(self):
        self.client.force_login(self.user)
        form_data = {
            'name': 'Delta Partners',
            'description': 'Partnership firm',
            'opening_balance': '2500.00',
            'status': 'ACTIVE',
            'created_date': '2026-06-10',
        }
        response = self.client.post(reverse('company-account-add'), data=form_data)
        self.assertRedirects(response, reverse('company-account-list'))
        self.assertTrue(CompanyAccount.objects.filter(user=self.user, name='Delta Partners').exists())

    def test_company_dashboard_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('company-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aggregate Business Balance')


class CompanyTransactionCRUDViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='txnuser', password='password123')
        self.company = CompanyAccount.objects.create(
            user=self.user,
            name='Omega Co',
            opening_balance=Decimal('500.00'),
            status='ACTIVE'
        )
        self.category = Category.objects.create(user=self.user, name='Utilities')

    def test_income_create_and_delete(self):
        self.client.force_login(self.user)
        form_data = {
            'company_account': self.company.pk,
            'amount': '1200.00',
            'source': 'Consulting Fee',
            'date': '2026-06-10',
            'description': 'Initial deposit'
        }
        response = self.client.post(reverse('company-income-add'), data=form_data)
        self.assertEqual(response.status_code, 302)
        
        income = CompanyIncome.objects.get(company_account=self.company, source='Consulting Fee')
        self.assertEqual(income.amount, Decimal('1200.00'))

        # Delete Income
        response = self.client.post(reverse('company-income-delete', args=[income.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CompanyIncome.objects.filter(pk=income.pk).exists())

    def test_expense_create_and_delete(self):
        self.client.force_login(self.user)
        form_data = {
            'company_account': self.company.pk,
            'name': 'Electric bill',
            'category': self.category.pk,
            'amount': '150.00',
            'date': '2026-06-10',
            'description': 'HQ electricity'
        }
        response = self.client.post(reverse('company-expense-add'), data=form_data)
        self.assertEqual(response.status_code, 302)

        expense = CompanyExpense.objects.get(company_account=self.company, name='Electric bill')
        self.assertEqual(expense.amount, Decimal('150.00'))

        # Delete Expense
        response = self.client.post(reverse('company-expense-delete', args=[expense.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CompanyExpense.objects.filter(pk=expense.pk).exists())


class CompanyReportsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reportuser', password='password123')
        self.company = CompanyAccount.objects.create(
            user=self.user,
            name='Alpha Corp',
            opening_balance=Decimal('1000.00'),
            status='ACTIVE'
        )
        self.income = CompanyIncome.objects.create(
            company_account=self.company,
            amount=Decimal('500.00'),
            source='Sales',
            date=datetime.date(2026, 6, 1)
        )
        self.category = Category.objects.create(user=self.user, name='Hosting')
        self.expense = CompanyExpense.objects.create(
            company_account=self.company,
            name='Server',
            amount=Decimal('200.00'),
            category=self.category,
            date=datetime.date(2026, 6, 5)
        )

    def test_reports_view_and_filtering(self):
        self.client.force_login(self.user)
        
        # Access reports dashboard (by default it filters current month, containing June 2026)
        response = self.client.get(reverse('company-reports') + '?date_filter=this_month')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha Corp')
        self.assertEqual(response.context['total_income'], Decimal('500.00'))
        self.assertEqual(response.context['total_expenses'], Decimal('200.00'))
        self.assertEqual(response.context['net_balance'], Decimal('300.00'))

        # Check Categorywise summary
        category_report = response.context['category_report']
        self.assertEqual(len(category_report), 1)
        self.assertEqual(category_report[0]['name'], 'Hosting')
        self.assertEqual(category_report[0]['amount'], Decimal('200.00'))
