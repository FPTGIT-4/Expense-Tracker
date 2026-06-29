from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from decimal import Decimal

class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profiletest', 
            password='password123',
            email='test@example.com',
            first_name='John',
            last_name='Doe'
        )

    def test_profile_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('profile'))
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")

    def test_profile_renders_logged_in_user_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/profile.html')
        
        # Verify details in output
        self.assertContains(response, 'profiletest')
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Date Joined')

    def test_password_change_url_resolves(self):
        url = reverse('password_change')
        self.assertEqual(resolve(url).view_name, 'password_change')


class UserSettingsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='settingstest',
            password='password123',
            email='settings@example.com',
            first_name='Alice',
            last_name='Smith'
        )

    def test_settings_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('settings'))
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('settings')}")

    def test_settings_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/settings.html')
        
        # Verify details in output
        self.assertContains(response, 'settingstest')
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'settings@example.com')

    def test_settings_saves_preferences_and_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('settings'), {
            'first_name': 'Bob',
            'last_name': 'Smith',
            'email': 'bob@example.com',
            'currency': '$',
        })
        self.assertRedirects(response, reverse('settings'))
        
        # Check user settings and profile details updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Bob')
        self.assertEqual(self.user.email, 'bob@example.com')
        self.assertEqual(self.user.settings.currency, '$')

    def test_settings_low_balance_alert_boundary(self):
        from accounts.models import Account
        from income.models import Income
        import datetime
        from decimal import Decimal
        account = Account.objects.create(
            user=self.user,
            name='Boundary Account',
            account_type='Cash',
            initial_balance=Decimal('50.00'),
            minimum_balance=Decimal('50.00')
        )
        self.assertTrue(account.is_below_minimum)
        
        # Balance goes above threshold by 1 cent
        Income.objects.create(
            user=self.user,
            account=account,
            amount=Decimal('0.01'),
            source='Salary',
            date=datetime.date.today()
        )
        self.assertFalse(account.is_below_minimum)






from accounts.models import Account

class AccountDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='detailtest',
            password='password123',
            email='detail@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='password123',
            email='other@example.com'
        )
        self.account = Account.objects.create(
            user=self.user,
            name='Test Bank Account',
            account_type='Bank Account',
            initial_balance=100.00
        )
        self.other_account = Account.objects.create(
            user=self.other_user,
            name='Other User Bank Account',
            account_type='Bank Account',
            initial_balance=200.00
        )





from income.forms import IncomeForm
from expenses.forms import ExpenseForm

class AccountStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='statususer',
            password='password123',
            email='status@example.com'
        )
        self.active_acc = Account.objects.create(
            user=self.user,
            name='Active Acc',
            account_type='Bank Account',
            initial_balance=Decimal('100.00'),
            status='ACTIVE'
        )
        self.inactive_acc = Account.objects.create(
            user=self.user,
            name='Inactive Acc',
            account_type='Cash',
            initial_balance=Decimal('100.00'),
            status='INACTIVE'
        )
        self.closed_acc = Account.objects.create(
            user=self.user,
            name='Closed Acc',
            account_type='Cash',
            initial_balance=Decimal('100.00'),
            status='CLOSED'
        )

    def test_default_status_is_active(self):
        acc = Account.objects.create(
            user=self.user,
            name='Default Status Acc',
            account_type='Cash'
        )
        self.assertEqual(acc.status, 'ACTIVE')

    def test_closed_account_hidden_from_dropdowns(self):
        # Test IncomeForm
        income_form = IncomeForm(user=self.user)
        queryset = income_form.fields['account'].queryset
        self.assertIn(self.active_acc, queryset)
        self.assertIn(self.inactive_acc, queryset)
        self.assertNotIn(self.closed_acc, queryset)

        # Test ExpenseForm
        expense_form = ExpenseForm(user=self.user)
        queryset = expense_form.fields['account'].queryset
        self.assertIn(self.active_acc, queryset)
        self.assertIn(self.inactive_acc, queryset)
        self.assertNotIn(self.closed_acc, queryset)



    def test_inactive_and_closed_accounts_fail_transaction_validation(self):
        # Test IncomeForm with Inactive Account
        form_data = {
            'account': self.inactive_acc.pk,
            'amount': 50.00,
            'source': 'Salary',
            'date': '2026-06-06',
            'description': ''
        }
        form = IncomeForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('account', form.errors)
        self.assertIn("Cannot create transactions for an inactive account.", form.errors['account'])

        # Test IncomeForm with Closed Account
        # (Even if hidden from dropdown, if posted manually it should fail validation)
        form_data['account'] = self.closed_acc.pk
        form = IncomeForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Select a valid choice. That choice is not one of the available choices.", form.errors['account'])




from accounts.forms import AccountForm

class AccountNotesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notesuser',
            password='password123',
            email='notes@example.com'
        )

    def test_default_notes_is_null(self):
        acc = Account.objects.create(
            user=self.user,
            name='No Notes Acc',
            account_type='Cash'
        )
        self.assertIsNone(acc.notes)

    def test_form_saves_notes(self):
        form_data = {
            'name': 'Test Saving Notes Acc',
            'account_type': 'Cash',
            'initial_balance': 150.00,
            'status': 'ACTIVE',
            'notes': 'This is a test multiline\nnotes field value.'
        }
        form = AccountForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        acc = form.save(commit=False)
        acc.user = self.user
        acc.save()

        # Retrieve and verify
        db_acc = Account.objects.get(pk=acc.pk)
        self.assertEqual(db_acc.notes, 'This is a test multiline\nnotes field value.')

class AccountIconTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='iconuser',
            password='password123',
            email='icon@example.com'
        )

    def _make_account(self, account_type):
        return Account.objects.create(
            user=self.user,
            name=f'{account_type} Acc',
            account_type=account_type,
            initial_balance=100.00
        )

    def test_cash_icon_and_color(self):
        acc = self._make_account('Cash')
        self.assertEqual(acc.bootstrap_icon, 'bi-cash-coin')
        self.assertEqual(acc.theme_color_class, 'color-1')

    def test_bank_account_icon_and_color(self):
        acc = self._make_account('Bank Account')
        self.assertEqual(acc.bootstrap_icon, 'bi-bank')
        self.assertEqual(acc.theme_color_class, 'color-2')

    def test_wallet_icon_and_color(self):
        acc = self._make_account('Wallet')
        self.assertEqual(acc.bootstrap_icon, 'bi-wallet2')
        self.assertEqual(acc.theme_color_class, 'color-2')

    def test_credit_card_icon_and_color(self):
        acc = self._make_account('Credit Card')
        self.assertEqual(acc.bootstrap_icon, 'bi-credit-card')
        self.assertEqual(acc.theme_color_class, 'color-3')

    def test_upi_icon_and_color(self):
        acc = self._make_account('UPI')
        self.assertEqual(acc.bootstrap_icon, 'bi-qr-code')
        self.assertEqual(acc.theme_color_class, 'color-1')

    def test_icon_appears_in_account_list(self):
        acc = self._make_account('Cash')
        self.client.force_login(self.user)
        response = self.client.get(reverse('account-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bi-cash-coin')




class LowBalanceThresholdTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='thresholduser', password='password123')

    def test_threshold_cannot_exceed_initial_balance(self):
        from accounts.models import Account
        from django.core.exceptions import ValidationError
        from decimal import Decimal

        with self.assertRaises(ValidationError):
            acc = Account(
                user=self.user,
                name='Invalid Threshold Account',
                account_type='Cash',
                initial_balance=Decimal('100.00'),
                minimum_balance=Decimal('150.00')
            )
            acc.full_clean()

    def test_threshold_cannot_be_negative(self):
        from accounts.models import Account
        from django.core.exceptions import ValidationError
        from decimal import Decimal

        with self.assertRaises(ValidationError):
            acc = Account(
                user=self.user,
                name='Negative Threshold Account',
                account_type='Cash',
                initial_balance=Decimal('100.00'),
                minimum_balance=Decimal('-10.00')
            )
            acc.full_clean()

    def test_threshold_change_requires_explicit_edit_flag(self):
        from accounts.models import Account
        from django.core.exceptions import ValidationError
        from decimal import Decimal

        acc = Account.objects.create(
            user=self.user,
            name='Test Explicit Edit Account',
            account_type='Cash',
            initial_balance=Decimal('100.00'),
            minimum_balance=Decimal('50.00')
        )

        # Try to modify minimum_balance directly without form or setting _explicit_threshold_edit
        acc.minimum_balance = Decimal('60.00')
        with self.assertRaises(ValidationError):
            acc.save()

        # Set the flag and save should work
        acc._explicit_threshold_edit = True
        acc.save()
        acc.refresh_from_db()
        self.assertEqual(acc.minimum_balance, Decimal('60.00'))


class GlobalFormsContextProcessorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='globalformstest',
            password='password123',
            email='globalformstest@example.com'
        )

    def test_anonymous_user_has_no_global_forms(self):
        from django.test import RequestFactory
        from accounts.context_processors import global_forms
        from django.contrib.auth.models import AnonymousUser
        
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        context = global_forms(request)
        self.assertIsNone(context['global_income_form'])
        self.assertIsNone(context['global_expense_form'])
        self.assertIsNone(context['global_account_form'])

    def test_authenticated_user_has_global_forms(self):
        from django.test import RequestFactory
        from accounts.context_processors import global_forms
        
        request = RequestFactory().get('/')
        request.user = self.user
        context = global_forms(request)
        
        self.assertIsNotNone(context['global_income_form'])
        self.assertIsNotNone(context['global_expense_form'])
        self.assertIsNotNone(context['global_account_form'])





