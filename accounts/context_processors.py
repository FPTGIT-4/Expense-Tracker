from .models import UserSettings, Account

def user_settings(request):
    if request.user.is_authenticated:
        settings, created = UserSettings.objects.get_or_create(user=request.user)

        # Compute low-balance alerts, respecting all new settings
        global_accounts_below_minimum = []
        global_low_balance_count = 0

        if settings.low_balance_alerts:
            qs = Account.objects.filter(user=request.user)

            # Apply scope filter
            scope = settings.low_balance_alert_scope
            if scope == 'active':
                qs = qs.filter(status='ACTIVE')
            elif scope == 'non_zero':
                # Accounts that have at least one income or expense
                from django.db.models import Q
                qs = qs.filter(
                    Q(incomes__isnull=False) | Q(expenses__isnull=False)
                ).distinct()
            # 'all' = no extra filter

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
    }


def global_forms(request):
    if request.user.is_authenticated:
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


