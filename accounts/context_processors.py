from .models import UserSettings, Account

def prefill_user_caches(user):
    if not user.is_authenticated:
        return
        
    if getattr(user, '_user_caches_prefilled', False):
        return

    from accounts.models import UserSettings, Account, annotate_balance
    from categories.models import Label, Category
    from decimal import Decimal

    # 1. User Settings
    settings, created = UserSettings.objects.get_or_create(user=user)
    user._settings_cache = settings

    # 2. Accounts
    all_accounts = list(annotate_balance(Account.objects.filter(user=user)))
    
    # If no accounts exist, create the default Cash account
    if not all_accounts:
        new_acc = Account.objects.create(
            user=user,
            name='Cash',
            account_type='Cash',
            initial_balance=Decimal('0.00')
        )
        new_acc.user = user
        new_acc._current_balance_cache = Decimal('0.00')
        all_accounts = [new_acc]
        
    for acc in all_accounts:
        acc.user = user
        
    user._all_accounts_cache = all_accounts
    user._active_accounts_cache = [acc for acc in all_accounts if acc.status != 'CLOSED']

    # 3. Labels
    user._labels_cache = list(Label.objects.filter(user=user))

    # 4. Categories
    user._categories_cache = list(Category.objects.filter(user=user))

    user._user_caches_prefilled = True


def user_settings(request):
    if request.user.is_authenticated:
        prefill_user_caches(request.user)
        settings = request.user._settings_cache

        # Compute low-balance alerts, respecting all new settings
        global_accounts_below_minimum = []
        global_low_balance_count = 0

        if settings.low_balance_alerts:
            scope = settings.low_balance_alert_scope
            if scope == 'active':
                qs = [acc for acc in request.user._all_accounts_cache if acc.status == 'ACTIVE']
            elif scope == 'non_zero':
                qs = [
                    acc for acc in request.user._all_accounts_cache 
                    if acc._total_income or acc._total_expense or acc._incoming_transfers or acc._outgoing_transfers
                ]
            else:
                qs = request.user._all_accounts_cache

            try:
                global_accounts_below_minimum = [acc for acc in qs if acc.is_below_minimum]
                global_low_balance_count = len(global_accounts_below_minimum)
            except Exception:
                global_accounts_below_minimum = []
                global_low_balance_count = 0

        return {
            'currency_symbol': settings.currency,
            'budget_threshold': settings.budget_threshold,
            'user_settings': settings,
            'global_accounts_below_minimum': global_accounts_below_minimum,
            'accounts_below_minimum': global_accounts_below_minimum,
            'global_low_balance_count': global_low_balance_count,
            'low_balance_count': global_low_balance_count,
            # Granular display flags
            'lba_show_navbar':   settings.low_balance_alerts and settings.low_balance_show_navbar_badge,
            'lba_show_banner':   settings.low_balance_alerts and settings.low_balance_show_dashboard_banner,
            'lba_show_panel':    settings.low_balance_alerts and settings.low_balance_show_dashboard_panel,
            # Appearance
            'user_dark_mode': settings.dark_mode,
        }
    return {
        'currency_symbol': '₹',
        'budget_threshold': 80,
        'user_settings': None,
        'global_accounts_below_minimum': [],
        'accounts_below_minimum': [],
        'global_low_balance_count': 0,
        'low_balance_count': 0,
        'lba_show_navbar': False,
        'lba_show_banner': False,
        'lba_show_panel':  False,
        'user_dark_mode':  True,
    }


def global_forms(request):
    if request.user.is_authenticated:
        prefill_user_caches(request.user)
        from income.forms import IncomeForm
        from expenses.forms import ExpenseForm
        from accounts.forms import AccountForm, TransferForm
        from budgets.forms import BudgetForm
        
        return {
            'global_income_form': IncomeForm(user=request.user),
            'global_expense_form': ExpenseForm(user=request.user),
            'global_transfer_form': TransferForm(user=request.user),
            'global_account_form': AccountForm(),
            'global_budget_form': BudgetForm(user=request.user),
        }
    return {
        'global_income_form': None,
        'global_expense_form': None,
        'global_transfer_form': None,
        'global_account_form': None,
        'global_budget_form': None,
    }


