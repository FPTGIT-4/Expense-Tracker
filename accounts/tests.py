from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User

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
            'budget_threshold': 90,
            'enable_budget_alerts': True,
            'low_balance_alerts': True,
            'low_balance_show_navbar_badge': True,
            'low_balance_show_dashboard_banner': True,
            'low_balance_show_dashboard_panel': True,
            'low_balance_alert_scope': 'active',
            'low_balance_default_minimum': '0.00',
        })
        self.assertRedirects(response, reverse('settings'))
        
        # Check user settings and profile details updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Bob')
        self.assertEqual(self.user.email, 'bob@example.com')
        self.assertEqual(self.user.settings.currency, '$')
        self.assertEqual(self.user.settings.budget_threshold, 90)

    def test_settings_low_balance_alert_suppression(self):
        from accounts.models import UserSettings, Account
        from decimal import Decimal
        
        self.client.force_login(self.user)
        settings, _ = UserSettings.objects.get_or_create(user=self.user)
        account = Account.objects.create(
            user=self.user,
            name='Test Account',
            account_type='Cash',
            initial_balance=Decimal('50.00'),
            minimum_balance=Decimal('50.00')
        )
        
        # Verify account is below minimum initially (alerts enabled)
        self.assertTrue(account.is_below_minimum)
        
        # Disable alerts in settings
        settings.low_balance_alerts = False
        settings.save()
        
        # Re-fetch account and verify is_below_minimum is False now
        account.refresh_from_db()
        self.assertFalse(account.is_below_minimum)

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

    def test_detail_view_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('account-detail', args=[self.account.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_detail_view_renders_user_account(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('account-detail', args=[self.account.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_detail.html')
        self.assertContains(response, 'Test Bank Account')
        self.assertContains(response, 'Bank Account')
        self.assertContains(response, '100.00')

    def test_detail_view_prevents_viewing_others_account(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('account-detail', args=[self.other_account.pk]))
        self.assertEqual(response.status_code, 404)

    def test_detail_view_calculates_analytics_and_transactions(self):
        from income.models import Income
        from expenses.models import Expense
        from categories.models import Category
        import datetime

        # Create income and expense associated with self.account
        category = Category.objects.create(user=self.user, name='Utilities')
        Income.objects.create(
            user=self.user,
            account=self.account,
            amount=50.00,
            source='Salary',
            date=datetime.date.today()
        )
        Expense.objects.create(
            user=self.user,
            account=self.account,
            amount=30.00,
            category=category,
            date=datetime.date.today()
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('account-detail', args=[self.account.pk]))
        self.assertEqual(response.status_code, 200)

        # Check net_change and transaction list inside context
        self.assertIn('net_change', response.context)
        self.assertEqual(response.context['net_change'], 20.00)

        # Check transactions list inside context
        self.assertIn('transactions', response.context)
        transactions = response.context['transactions']
        self.assertEqual(len(transactions), 2)


from decimal import Decimal
from accounts.models import AccountTransfer
from accounts.forms import TransferForm

class AccountTransferTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='transferuser',
            password='password123',
            email='transfer@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser2',
            password='password123',
            email='other2@example.com'
        )
        self.acc_a = Account.objects.create(
            user=self.user,
            name='Account A',
            account_type='Bank Account',
            initial_balance=Decimal('500.00')
        )
        self.acc_b = Account.objects.create(
            user=self.user,
            name='Account B',
            account_type='Cash',
            initial_balance=Decimal('100.00')
        )
        self.other_acc = Account.objects.create(
            user=self.other_user,
            name='Other Account',
            account_type='Cash',
            initial_balance=Decimal('100.00')
        )

    def test_transfer_view_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('account-transfer'))
        self.assertNotEqual(response.status_code, 200)

    def test_transfer_form_filters_user_accounts(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('account-transfer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_transfer_form.html')
        form = response.context['form']
        
        # Check that from_account and to_account only list the user's accounts
        from_queryset = form.fields['from_account'].queryset
        to_queryset = form.fields['to_account'].queryset
        self.assertIn(self.acc_a, from_queryset)
        self.assertIn(self.acc_b, from_queryset)
        self.assertNotIn(self.other_acc, from_queryset)

    def test_transfer_validation_prevents_same_account(self):
        self.client.force_login(self.user)
        form_data = {
            'from_account': self.acc_a.pk,
            'to_account': self.acc_a.pk,
            'amount': 50.00,
            'transfer_date': '2026-06-06',
            'note': 'Self transfer'
        }
        response = self.client.post(reverse('account-transfer'), data=form_data)
        self.assertEqual(response.status_code, 200) # Form invalid, redisplayed
        self.assertFormError(response.context['form'], None, "Source and destination accounts cannot be the same.")

    def test_transfer_validation_prevents_insufficient_funds(self):
        self.client.force_login(self.user)
        form_data = {
            'from_account': self.acc_a.pk,
            'to_account': self.acc_b.pk,
            'amount': 600.00,
            'transfer_date': '2026-06-06',
            'note': 'Overdraft'
        }
        response = self.client.post(reverse('account-transfer'), data=form_data)
        self.assertEqual(response.status_code, 200) # Form invalid, redisplayed
        self.assertFormError(response.context['form'], 'amount', "Insufficient funds in Account A. Current balance: ₹500.00")

    def test_transfer_validation_prevents_negative_amount(self):
        self.client.force_login(self.user)
        form_data = {
            'from_account': self.acc_a.pk,
            'to_account': self.acc_b.pk,
            'amount': -10.00,
            'transfer_date': '2026-06-06',
            'note': 'Negative amount'
        }
        response = self.client.post(reverse('account-transfer'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'amount', "Transfer amount must be a positive number.")

    def test_successful_transfer_updates_balances(self):
        self.client.force_login(self.user)
        form_data = {
            'from_account': self.acc_a.pk,
            'to_account': self.acc_b.pk,
            'amount': 200.00,
            'transfer_date': '2026-06-06',
            'note': 'Valid transfer'
        }
        response = self.client.post(reverse('account-transfer'), data=form_data)
        self.assertRedirects(response, reverse('account-list'))
        
        # Verify db model instance exists
        transfers = AccountTransfer.objects.all()
        self.assertEqual(transfers.count(), 1)
        transfer = transfers.first()
        self.assertEqual(transfer.amount, Decimal('200.00'))
        
        # Verify dynamic balances have updated
        self.assertEqual(self.acc_a.current_balance, Decimal('300.00'))
        self.assertEqual(self.acc_b.current_balance, Decimal('300.00'))


import datetime
from django.utils import timezone
from unittest.mock import patch

class TransferHistoryTests(TestCase):
    def setUp(self):
        self.localdate_patcher = patch('django.utils.timezone.localdate')
        self.mock_localdate = self.localdate_patcher.start()
        self.mock_localdate.return_value = datetime.date(2026, 6, 10)

        self.user = User.objects.create_user(
            username='historyuser',
            password='password123',
            email='history@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser3',
            password='password123',
            email='other3@example.com'
        )
        self.acc_a = Account.objects.create(
            user=self.user,
            name='Wallet A',
            account_type='Bank Account',
            initial_balance=Decimal('1000.00')
        )
        self.acc_b = Account.objects.create(
            user=self.user,
            name='Wallet B',
            account_type='Cash',
            initial_balance=Decimal('500.00')
        )
        self.other_acc = Account.objects.create(
            user=self.other_user,
            name='Other Wallet',
            account_type='Cash',
            initial_balance=Decimal('500.00')
        )
        self.other_acc_b = Account.objects.create(
            user=self.other_user,
            name='Other Wallet B',
            account_type='Cash',
            initial_balance=Decimal('500.00')
        )
        
        # Create transfers with different dates and notes for testing filters/search
        today = timezone.localdate()
        self.t1 = AccountTransfer.objects.create(
            user=self.user,
            from_account=self.acc_a,
            to_account=self.acc_b,
            amount=Decimal('50.00'),
            transfer_date=today,
            note="Groceries allocation"
        )
        
        self.t2 = AccountTransfer.objects.create(
            user=self.user,
            from_account=self.acc_b,
            to_account=self.acc_a,
            amount=Decimal('120.00'),
            transfer_date=today - datetime.timedelta(days=2),
            note="Refund from Wallet B"
        )

        self.t3 = AccountTransfer.objects.create(
            user=self.user,
            from_account=self.acc_a,
            to_account=self.acc_b,
            amount=Decimal('15.00'),
            transfer_date=today - datetime.timedelta(days=10),
            note="Old pocket transfer"
        )
        
        # Other user's transfer (should not show up)
        self.other_t = AccountTransfer.objects.create(
            user=self.other_user,
            from_account=self.other_acc,
            to_account=self.other_acc_b,
            amount=Decimal('10.00'),
            transfer_date=today,
            note="Secret transfer"
        )

    def test_transfer_list_view_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('transfer-list'))
        self.assertNotEqual(response.status_code, 200)

    def test_transfer_list_renders_logged_in_user_transfers(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('transfer-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/transfer_list.html')
        
        # Should display user transfers but NOT other user's
        self.assertContains(response, 'Groceries allocation')
        self.assertContains(response, 'Refund from Wallet B')
        self.assertContains(response, 'Old pocket transfer')
        self.assertNotContains(response, 'Secret transfer')

    def test_transfer_list_search_filters_results(self):
        self.client.force_login(self.user)
        
        # Search by note
        response = self.client.get(reverse('transfer-list') + '?q=Groceries')
        self.assertContains(response, 'Groceries allocation')
        self.assertNotContains(response, 'Refund from Wallet B')

        # Search by account name
        response = self.client.get(reverse('transfer-list') + '?q=Wallet B')
        self.assertContains(response, 'Groceries allocation') # Wallet A to Wallet B
        self.assertContains(response, 'Refund from Wallet B') # Wallet B to Wallet A

        # Search by exact amount
        response = self.client.get(reverse('transfer-list') + '?q=120')
        self.assertContains(response, 'Refund from Wallet B')
        self.assertNotContains(response, 'Groceries allocation')

    def test_transfer_list_period_filters(self):
        self.client.force_login(self.user)

        # Today filter
        response = self.client.get(reverse('transfer-list') + '?period=today')
        self.assertContains(response, 'Groceries allocation')
        self.assertNotContains(response, 'Refund from Wallet B')
        self.assertNotContains(response, 'Old pocket transfer')

        # Week filter (today is Sat/Sun etc, but -2 days is in the same week, -10 days is not)
        response = self.client.get(reverse('transfer-list') + '?period=week')
        self.assertContains(response, 'Groceries allocation')
        self.assertContains(response, 'Refund from Wallet B')
        self.assertNotContains(response, 'Old pocket transfer')

        # Month filter (-10 days might be in same month, let's just make it -35 days to be sure)
        # We will make sure t3 is 35 days ago to test month/year properly
        self.t3.transfer_date = timezone.localdate() - datetime.timedelta(days=35)
        self.t3.save()
        
        response = self.client.get(reverse('transfer-list') + '?period=month')
        self.assertContains(response, 'Groceries allocation')
        self.assertContains(response, 'Refund from Wallet B')
        self.assertNotContains(response, 'Old pocket transfer')

        # Year filter (all 3 should show if within the same year)
        response = self.client.get(reverse('transfer-list') + '?period=year')
        self.assertContains(response, 'Groceries allocation')
        self.assertContains(response, 'Refund from Wallet B')
        self.assertContains(response, 'Old pocket transfer')

    def test_transfer_detail_view_permissions_and_rendering(self):
        self.client.force_login(self.user)
        
        # Access own transfer detail
        response = self.client.get(reverse('transfer-detail', args=[self.t1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/transfer_detail.html')
        self.assertContains(response, 'Groceries allocation')
        self.assertContains(response, 'Wallet A')
        self.assertContains(response, 'Wallet B')
        self.assertContains(response, '50.00')

        # Try to access other user's transfer detail (should fail with 404)
        response = self.client.get(reverse('transfer-detail', args=[self.other_t.pk]))
        self.assertEqual(response.status_code, 404)

    def tearDown(self):
        self.localdate_patcher.stop()


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

        # Test TransferForm
        transfer_form = TransferForm(user=self.user)
        from_qs = transfer_form.fields['from_account'].queryset
        to_qs = transfer_form.fields['to_account'].queryset
        self.assertIn(self.active_acc, from_qs)
        self.assertNotIn(self.closed_acc, from_qs)
        self.assertIn(self.active_acc, to_qs)
        self.assertNotIn(self.closed_acc, to_qs)

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

    def test_transfers_validation_with_status_rules(self):
        # Transfer from INACTIVE should fail
        transfer = AccountTransfer(
            user=self.user,
            from_account=self.inactive_acc,
            to_account=self.active_acc,
            amount=Decimal('10.00'),
            transfer_date=timezone.localdate()
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as context:
            transfer.clean()
        self.assertIn('from_account', context.exception.message_dict)

        # Transfer to CLOSED should fail
        transfer2 = AccountTransfer(
            user=self.user,
            from_account=self.active_acc,
            to_account=self.closed_acc,
            amount=Decimal('10.00'),
            transfer_date=timezone.localdate()
        )
        with self.assertRaises(ValidationError) as context:
            transfer2.clean()
        self.assertIn('to_account', context.exception.message_dict)


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

    def test_detail_view_renders_notes(self):
        acc = Account.objects.create(
            user=self.user,
            name='Notes Rendering Acc',
            account_type='Cash',
            notes='Render this multiline note.'
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('account-detail', args=[acc.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_detail.html')
        self.assertContains(response, 'Account Note')
        self.assertContains(response, 'Render this multiline note.')


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

    def test_icon_appears_in_account_detail(self):
        acc = self._make_account('Bank Account')
        self.client.force_login(self.user)
        response = self.client.get(reverse('account-detail', args=[acc.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bi-bank')


class TransferFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='transferuser', password='password123')

    def test_transfer_form_date_defaults_to_today(self):
        from accounts.forms import TransferForm
        from django.utils import timezone
        form = TransferForm(user=self.user)
        self.assertEqual(form.fields['transfer_date'].initial, timezone.localdate())


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
        self.assertIsNone(context['global_transfer_form'])
        self.assertIsNone(context['global_account_form'])
        self.assertIsNone(context['global_budget_form'])

    def test_authenticated_user_has_global_forms(self):
        from django.test import RequestFactory
        from accounts.context_processors import global_forms
        
        request = RequestFactory().get('/')
        request.user = self.user
        context = global_forms(request)
        
        self.assertIsNotNone(context['global_income_form'])
        self.assertIsNotNone(context['global_expense_form'])
        self.assertIsNotNone(context['global_transfer_form'])
        self.assertIsNotNone(context['global_account_form'])
        self.assertIsNotNone(context['global_budget_form'])



