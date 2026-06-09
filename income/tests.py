from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import IncomeForm
from accounts.models import Account

class IncomeFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_form_date_defaults_to_today(self):
        form = IncomeForm(user=self.user)
        self.assertEqual(form.fields['date'].initial, timezone.localdate())


class IncomeCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='incomeuser', password='password123')
        self.account = Account.objects.create(user=self.user, name='Cash', account_type='Cash')

    def test_income_create_view_post(self):
        from django.urls import reverse
        from .models import Income
        self.client.force_login(self.user)
        response = self.client.post(reverse('income-create'), {
            'account': self.account.id,
            'amount': '150.00',
            'source': 'Salary',
            'date': timezone.localdate().strftime('%Y-%m-%d'),
            'description': 'Monthly salary'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Income.objects.filter(user=self.user, amount='150.00').exists())

