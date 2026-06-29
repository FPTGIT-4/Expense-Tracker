from .models import UserSettings, Account

def prefill_user_caches(user):
    if not user.is_authenticated:
        return
        
    if getattr(user, '_user_caches_prefilled', False):
        return

    from accounts.models import UserSettings, Account, annotate_balance
    from categories.models import Category
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



    # 4. Categories
    user._categories_cache = list(Category.objects.filter(user=user))

    user._user_caches_prefilled = True


def user_settings(request):
    if request.user.is_authenticated:
        prefill_user_caches(request.user)
        settings = request.user._settings_cache

        # Compute low-balance alerts, defaulting to active accounts
        global_accounts_below_minimum = []
        global_low_balance_count = 0

        qs = [acc for acc in request.user._all_accounts_cache if acc.status == 'ACTIVE']
        try:
            global_accounts_below_minimum = [acc for acc in qs if acc.is_below_minimum]
            global_low_balance_count = len(global_accounts_below_minimum)
        except Exception:
            pass

        return {
            'currency_symbol': settings.currency,
            'user_settings': settings,
            'global_accounts_below_minimum': global_accounts_below_minimum,
            'accounts_below_minimum': global_accounts_below_minimum,
            'global_low_balance_count': global_low_balance_count,
            'low_balance_count': global_low_balance_count,
            # Granular display flags (always True if alerts exist)
            'lba_show_navbar':   True,
            'lba_show_banner':   True,
            'lba_show_panel':    True,
            # Appearance
            'user_dark_mode': True,
        }
    return {
        'currency_symbol': '₹',
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
        from accounts.forms import AccountForm
        
        return {
            'global_income_form': IncomeForm(user=request.user),
            'global_expense_form': ExpenseForm(user=request.user),
            'global_account_form': AccountForm(),
        }
    return {
        'global_income_form': None,
        'global_expense_form': None,
        'global_account_form': None,
    }


