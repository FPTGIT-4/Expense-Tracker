from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
import json

from categories.models import Category
from accounts.models import Account
from income.models import Income
from expenses.models import Expense
from goals.models import Goal
from debts.models import Debt
from companies.models import CompanyAccount, CompanyIncome, CompanyExpense

class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.force_login(self.user)
        
        # Categories
        self.cat_food = Category.objects.create(user=self.user, name='Food')
        self.cat_salary = Category.objects.create(user=self.user, name='Salary')
        
        # Account
        self.account = Account.objects.create(
            user=self.user,
            name='Cash',
            account_type='Cash',
            initial_balance=Decimal('100.00')
        )
        
        # Personal Transactions
        Income.objects.create(
            user=self.user,
            account=self.account,
            amount=Decimal('1000.00'),
            source='Salary',
            date=datetime.date.today()
        )
        Expense.objects.create(
            user=self.user,
            account=self.account,
            name='Lunch',
            amount=Decimal('50.00'),
            category=self.cat_food,
            date=datetime.date.today()
        )
        
        # Company Account & Transactions
        self.company = CompanyAccount.objects.create(
            user=self.user,
            name='Consulting Corp',
            opening_balance=Decimal('5000.00')
        )
        CompanyIncome.objects.create(
            company_account=self.company,
            amount=Decimal('2500.00'),
            source='Project Alpha',
            date=datetime.date.today()
        )
        CompanyExpense.objects.create(
            company_account=self.company,
            name='SaaS Subscription',
            amount=Decimal('150.00'),
            category=self.cat_food,
            date=datetime.date.today()
        )
        
        # Goals
        Goal.objects.create(
            user=self.user,
            name='New Laptop',
            target_amount=Decimal('1500.00'),
            current_amount=Decimal('300.00')
        )
        
        # Debts
        Debt.objects.create(
            user=self.user,
            person_name='John Doe',
            debt_type='Borrowed',
            amount=Decimal('200.00'),
            status='Active'
        )

    def test_analytics_dashboard_view_status(self):
        response = self.client.get(reverse('analytics-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/dashboard.html')

    def test_aggregations_and_kpis(self):
        response = self.client.get(reverse('analytics-dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check financial values
        # Personal: Income = 1000, Expense = 50
        # Company: Income = 2500, Expense = 150
        # Totals: Income = 3500, Expense = 200, Net Savings = 3300
        self.assertEqual(response.context['total_income'], Decimal('3500.00'))
        self.assertEqual(response.context['total_expenses'], Decimal('200.00'))
        self.assertEqual(response.context['net_savings'], Decimal('3300.00'))
        
        # Check cards and insights
        self.assertEqual(response.context['top_spending_category'], 'Food')
        self.assertEqual(response.context['highest_expense_amount'], Decimal('150.00'))
        self.assertEqual(response.context['highest_income_amount'], Decimal('2500.00'))
        
        # Goals & Debts
        self.assertEqual(response.context['total_goals_target'], Decimal('1500.00'))
        self.assertEqual(response.context['total_goals_current'], Decimal('300.00'))
        self.assertEqual(response.context['total_borrowed_remaining'], Decimal('200.00'))

        # Total Transactions
        # 1 personal inc, 1 personal exp, 1 company inc, 1 company exp = 4
        self.assertEqual(response.context['total_transactions_count'], 4)

    def test_date_filters(self):
        # Filter: Today
        response = self.client.get(reverse('analytics-dashboard'), {'date_filter': 'today'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_income'], Decimal('3500.00'))

        # Filter: Custom range (outside transaction date)
        past_date = (datetime.date.today() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.get(reverse('analytics-dashboard'), {
            'date_filter': 'custom',
            'start_date': past_date,
            'end_date': past_date
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_income'], Decimal('0.00'))

    def test_charts_data_serialization(self):
        response = self.client.get(reverse('analytics-dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify JSON properties
        chart_inc_vs_exp = json.loads(response.context['chart_inc_vs_exp'])
        self.assertIn('categories', chart_inc_vs_exp)
        self.assertIn('income', chart_inc_vs_exp)
        self.assertIn('expense', chart_inc_vs_exp)
        
        # Check series values
        self.assertEqual(chart_inc_vs_exp['income'], [1000.0, 2500.0])
        self.assertEqual(chart_inc_vs_exp['expense'], [50.0, 150.0])
        
        # Verify category dist has 'Food' and 200.0 (50 personal + 150 company)
        chart_category_dist = json.loads(response.context['chart_category_dist'])
        self.assertIn('Food', chart_category_dist['labels'])
        self.assertIn(200.0, chart_category_dist['series'])
