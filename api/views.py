from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import datetime

from accounts.models import Account, AccountTransfer, UserSettings
from categories.models import Category
from income.models import Income
from expenses.models import Expense
from budgets.models import Budget
from reports.services import ReportDataService
from budgets.models import get_budget_alerts, get_budget_alert_count

from .serializers import (
    UserSerializer, UserSettingsSerializer, RegisterSerializer,
    AccountSerializer, AccountTransferSerializer, CategorySerializer,
    IncomeSerializer, ExpenseSerializer, BudgetSerializer
)

# ── Authentication Views ──────────────────────────────────────────────

class LoginAPIView(ObtainAuthToken):
    """
    Takes user credentials and returns a token along with user profile information.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        user_serializer = UserSerializer(user)
        return Response({
            'token': token.key,
            'user': user_serializer.data
        })

class LogoutAPIView(APIView):
    """
    Invalidates/deletes the user's active token.
    """
    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
            return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Token invalid or not found.'}, status=status.HTTP_400_BAD_REQUEST)

class RegisterAPIView(generics.CreateAPIView):
    """
    Registers a new user and returns their token and profile.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        user_serializer = UserSerializer(user)
        return Response({
            'token': token.key,
            'user': user_serializer.data
        }, status=status.HTTP_201_CREATED)

# ── Settings Endpoint ───────────────────────────────────────────────────

class UserSettingsAPIView(generics.RetrieveUpdateAPIView):
    """
    Get or update the settings for the logged-in user.
    """
    serializer_class = UserSettingsSerializer

    def get_object(self):
        settings, created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings

# ── CRUD ViewSets ───────────────────────────────────────────────────────

class AccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Account model. Filters by authenticated user.
    Supports list, retrieve, create, update, delete.
    """
    serializer_class = AccountSerializer
    search_fields = ['name', 'account_type']
    ordering_fields = ['name', 'initial_balance', 'created_at']

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

class AccountTransferViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Account Transfers. Filtering and paginated.
    """
    serializer_class = AccountTransferSerializer
    ordering_fields = ['transfer_date', 'amount', 'created_at']

    def get_queryset(self):
        return AccountTransfer.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = AccountTransferSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category model. Filters by authenticated user.
    Enforces uniqueness per user.
    """
    serializer_class = CategorySerializer
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class IncomeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Income model.
    """
    serializer_class = IncomeSerializer
    filterset_fields = ['account', 'source', 'date']
    search_fields = ['source', 'description']
    ordering_fields = ['date', 'amount', 'created_at']

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)

class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Expense model.
    """
    serializer_class = ExpenseSerializer
    filterset_fields = ['account', 'category', 'date']
    search_fields = ['name', 'description']
    ordering_fields = ['date', 'amount', 'created_at']

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

class BudgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Budget model.
    """
    serializer_class = BudgetSerializer
    filterset_fields = ['category', 'month', 'year', 'is_active']
    ordering_fields = ['year', 'month', 'budget_amount']

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

# ── Custom Dynamic Endpoints ──────────────────────────────────────────

class DashboardSummaryAPIView(APIView):
    """
    API endpoint returning dashboard overview metrics.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.localdate()

        # Account list
        accounts = Account.objects.filter(user=user)
        total_balance = sum(acc.current_balance for acc in accounts)
        accounts_data = AccountSerializer(accounts, many=True).data

        # Income / Expense summaries (this month)
        start_of_month = today.replace(day=1)
        monthly_income = Income.objects.filter(
            user=user, date__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_expense = Expense.objects.filter(
            user=user, date__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Recent transactions (up to 10 combined)
        incomes = Income.objects.filter(user=user).order_by('-date', '-created_at')[:10]
        expenses = Expense.objects.filter(user=user).select_related('category').order_by('-date', '-created_at')[:10]

        recent_activity = []
        for inc in incomes:
            recent_activity.append({
                'id': inc.id,
                'type': 'Income',
                'amount': float(inc.amount),
                'category_or_source': inc.source,
                'date': inc.date.strftime('%Y-%m-%d'),
                'description': inc.description,
            })
        for exp in expenses:
            recent_activity.append({
                'id': exp.id,
                'type': 'Expense',
                'amount': float(exp.amount),
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'date': exp.date.strftime('%Y-%m-%d'),
                'description': exp.description,
            })
        recent_activity.sort(key=lambda x: x['date'], reverse=True)
        recent_activity = recent_activity[:10]

        # Budget alert warnings count
        budget_alerts_count = get_budget_alert_count(user, today.month, today.year)

        try:
            currency = user.settings.currency
        except Exception:
            currency = '₹'

        return Response({
            'currency_symbol': currency,
            'total_balance': float(total_balance),
            'monthly_income': float(monthly_income),
            'monthly_expense': float(monthly_expense),
            'net_savings': float(monthly_income - monthly_expense),
            'budget_alerts_count': budget_alerts_count,
            'recent_activity': recent_activity,
            'accounts': accounts_data
        })

class NotificationAPIView(APIView):
    """
    Returns alerts and warning notifications for budgets and accounts.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.localdate()

        # 1. Budget Alerts
        raw_budget_alerts = get_budget_alerts(user, today.month, today.year)
        budget_alerts = []
        for alert in raw_budget_alerts:
            budget_alerts.append({
                'type': alert['type'],
                'category_name': alert['budget'].category.name,
                'budget_amount': float(alert['amount']),
                'spent': float(alert['spent']),
                'usage_percentage': alert['usage_percentage'],
                'message': alert['message'],
            })

        # 2. Low Balance Alerts
        low_balance_alerts = []
        try:
            settings = user.settings
            show_alerts = settings.low_balance_alerts
        except Exception:
            show_alerts = True

        if show_alerts:
            accounts = Account.objects.filter(user=user)
            # Filter based on scope
            scope = 'active'
            try:
                scope = settings.low_balance_alert_scope
            except Exception:
                pass

            if scope == 'active':
                accounts = accounts.filter(status='ACTIVE')
            elif scope == 'non_zero':
                from django.db.models import Q
                accounts = accounts.filter(
                    Q(incomes__isnull=False) | Q(expenses__isnull=False)
                ).distinct()

            for acc in accounts:
                if acc.is_below_minimum:
                    low_balance_alerts.append({
                        'account_id': acc.id,
                        'name': acc.name,
                        'current_balance': float(acc.current_balance),
                        'threshold': float(acc.effective_minimum_balance),
                        'shortage': float(acc.shortage),
                        'coverage_percentage': acc.coverage_percentage,
                    })

        return Response({
            'budget_alerts': budget_alerts,
            'low_balance_alerts': low_balance_alerts
        })

class ReportAPIView(APIView):
    """
    Returns financial analytical reports based on start_date and end_date.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        date_filter = request.query_params.get('date_filter', 'this_month')
        today = timezone.localdate()

        # Resolve date range
        start_date = None
        end_date = today

        if date_filter == 'today':
            start_date = today
        elif date_filter == 'this_week':
            start_date = today - datetime.timedelta(days=today.weekday())
        elif date_filter == 'this_year':
            start_date = today.replace(month=1, day=1)
        elif date_filter == 'custom':
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid custom date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else: # default to this month
            start_date = today.replace(day=1)

        # Call existing service
        report_data = ReportDataService.get_report_data(user, start_date, end_date)

        # Format decimal/date fields to standard JSON floats/strings
        formatted_recent = []
        for tx in report_data['recent_transactions']:
            formatted_recent.append({
                'date': tx['date'].strftime('%Y-%m-%d'),
                'type': tx['type'],
                'category_or_source': tx['category_or_source'],
                'amount': float(tx['amount']),
                'description': tx['description'],
            })

        formatted_monthly = []
        for item in report_data['monthly_summary']:
            formatted_monthly.append({
                'month': item['month_date'].strftime('%Y-%m'),
                'income': float(item['income']),
                'expense': float(item['expense']),
                'balance': float(item['balance']),
            })

        formatted_cat_report = []
        for item in report_data['category_report']:
            formatted_cat_report.append({
                'name': item['name'],
                'amount': float(item['amount']),
                'percentage': item['percentage'],
            })

        formatted_src_report = []
        for item in report_data['source_report']:
            formatted_src_report.append({
                'source': item['source'],
                'amount': float(item['amount']),
            })

        return Response({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_income': float(report_data['total_income']),
            'total_expenses': float(report_data['total_expenses']),
            'net_balance': float(report_data['current_balance']),
            'total_transactions_count': report_data['total_transactions'],
            'category_expense_distribution': formatted_cat_report,
            'income_source_distribution': formatted_src_report,
            'recent_transactions': formatted_recent,
            'monthly_ledger': formatted_monthly,
        })
