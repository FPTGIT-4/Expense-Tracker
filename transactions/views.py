import json
import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.db import transaction

from income.models import Income
from expenses.models import Expense
from categories.models import Category
from accounts.models import Account


class AddTransactionView(LoginRequiredMixin, View):
    template_name = 'transactions/add_transaction.html'

    def get(self, request, *args, **kwargs):
        # Read ?tab=income or ?tab=expense to pre-select the right tab
        tab = request.GET.get('tab', 'income').strip().lower()
        initial_type = 'expense' if tab == 'expense' else 'income'

        # Ensure user has at least one account
        if not Account.objects.filter(user=request.user).exists():
            Account.objects.create(
                user=request.user,
                name='Cash',
                account_type='Cash',
                initial_balance=Decimal('0.00')
            )

        from django.utils import timezone
        context = {
            'today': timezone.localdate(),
            'source_choices': Income.SOURCE_CHOICES,
            'categories': Category.objects.filter(user=request.user).order_by('name'),
            'accounts': Account.objects.filter(user=request.user).exclude(status='CLOSED').order_by('name'),
            'initial_type': initial_type,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'success': False, 'errors': ['Invalid JSON payload.']}, status=400)

        transaction_type = data.get('type', '').strip().lower()
        date_str = data.get('date', '').strip()
        top_account_id = data.get('account', '')
        rows = data.get('rows', [])

        # --- Validate top-level fields ---
        errors = []

        if transaction_type not in ('income', 'expense'):
            errors.append('Transaction type must be "income" or "expense".')

        transaction_date = None
        try:
            transaction_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f'Invalid date format: "{date_str}". Expected YYYY-MM-DD.')

        if not isinstance(rows, list) or len(rows) == 0:
            errors.append('At least one row is required.')

        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        # --- Process each row ---
        created_count = 0

        try:
            with transaction.atomic():
                if transaction_type == 'income':
                    valid_sources = {choice[0] for choice in Income.SOURCE_CHOICES}
                    for i, row in enumerate(rows):
                        amount_str = str(row.get('amount', '')).strip()
                        source = row.get('source', '').strip()
                        desc = row.get('description', '').strip()
                        account_id = str(row.get('account', '')).strip() or str(top_account_id).strip()

                        try:
                            amount = Decimal(amount_str)
                            if amount <= 0:
                                errors.append(f'Row {i+1}: Amount must be positive.')
                        except (InvalidOperation, ValueError):
                            errors.append(f'Row {i+1}: Invalid amount format.')

                        if source not in valid_sources:
                            errors.append(f'Row {i+1}: Invalid source "{source}".')

                        if not account_id:
                            errors.append(f'Row {i+1}: Account selection is required.')
                        else:
                            try:
                                acc = Account.objects.get(pk=int(account_id), user=request.user)
                                if acc.status == 'CLOSED':
                                    errors.append(f'Row {i+1}: Cannot create transactions for a closed account.')
                                elif acc.status == 'INACTIVE':
                                    errors.append(f'Row {i+1}: Cannot create transactions for an inactive account.')
                            except (Account.DoesNotExist, ValueError):
                                errors.append(f'Row {i+1}: Invalid account selected.')

                    if errors:
                        return JsonResponse({'success': False, 'errors': errors}, status=400)

                    # Save all if validation passed
                    for row in rows:
                        amount = Decimal(str(row['amount']).strip())
                        source = row['source'].strip()
                        desc = row.get('description', '').strip()
                        account_id = int(str(row.get('account', '')).strip() or str(top_account_id).strip())
                        account = Account.objects.get(pk=account_id, user=request.user)
                        Income.objects.create(
                            user=request.user,
                            account=account,
                            amount=amount,
                            source=source,
                            date=transaction_date,
                            description=desc if desc else None
                        )
                        created_count += 1

                elif transaction_type == 'expense':
                    for i, row in enumerate(rows):
                        amount_str = str(row.get('amount', '')).strip()
                        cat_id = str(row.get('category', '')).strip()
                        desc = row.get('description', '').strip()
                        account_id = str(row.get('account', '')).strip() or str(top_account_id).strip()

                        try:
                            amount = Decimal(amount_str)
                            if amount <= 0:
                                errors.append(f'Row {i+1}: Amount must be positive.')
                        except (InvalidOperation, ValueError):
                            errors.append(f'Row {i+1}: Invalid amount format.')

                        if not cat_id or cat_id == '__none__':
                            errors.append(f'Row {i+1}: Category is required.')
                        else:
                            try:
                                Category.objects.get(pk=cat_id, user=request.user)
                            except (Category.DoesNotExist, ValueError):
                                errors.append(f'Row {i+1}: Invalid category.')

                        if not account_id:
                            errors.append(f'Row {i+1}: Account selection is required.')
                        else:
                            try:
                                acc = Account.objects.get(pk=int(account_id), user=request.user)
                                if acc.status == 'CLOSED':
                                    errors.append(f'Row {i+1}: Cannot create transactions for a closed account.')
                                elif acc.status == 'INACTIVE':
                                    errors.append(f'Row {i+1}: Cannot create transactions for an inactive account.')
                            except (Account.DoesNotExist, ValueError):
                                errors.append(f'Row {i+1}: Invalid account selected.')

                    if errors:
                        return JsonResponse({'success': False, 'errors': errors}, status=400)

                    # Save all if validation passed
                    for row in rows:
                        amount = Decimal(str(row['amount']).strip())
                        cat_id = str(row.get('category', '')).strip()
                        desc = row.get('description', '').strip()
                        account_id = int(str(row.get('account', '')).strip() or str(top_account_id).strip())
                        account = Account.objects.get(pk=account_id, user=request.user)

                        category = None
                        category_name = ""
                        if cat_id and cat_id != '__none__':
                            category = Category.objects.get(pk=cat_id, user=request.user)
                            category_name = category.name

                        # Fallback for name field on Expense model
                        expense_name = str(row.get('name', '')).strip()
                        if not expense_name:
                            expense_name = category_name
                        if not expense_name and desc:
                            expense_name = desc[:50]
                        if not expense_name:
                            expense_name = "Expense"

                        Expense.objects.create(
                            user=request.user,
                            account=account,
                            name=expense_name,
                            amount=amount,
                            date=transaction_date,
                            category=category,
                            description=desc if desc else None
                        )
                        created_count += 1
        except Exception as e:
            return JsonResponse({'success': False, 'errors': [f'Database error: {str(e)}']}, status=500)

        # Determine redirect path (for full page add)
        redirect_url = '/incomes/' if transaction_type == 'income' else '/expenses/'

        return JsonResponse({
            'success': True,
            'count': created_count,
            'redirect': redirect_url
        })


from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import TransactionHistory
from accounts.models import Account

class TransactionHistoryListView(LoginRequiredMixin, ListView):
    model = TransactionHistory
    template_name = 'transactions/transaction_history.html'
    context_object_name = 'history_list'
    paginate_by = 25

    def get_queryset(self):
        qs = TransactionHistory.objects.filter(user=self.request.user).select_related('account', 'to_account')

        # Apply search query
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(category_name__icontains=q) |
                Q(description__icontains=q) |
                Q(amount__icontains=q) |
                Q(activity_type__icontains=q) |
                Q(expense__name__icontains=q)
            )

        # Apply date filters
        date_from = self.request.GET.get('date_from', '').strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)

        date_to = self.request.GET.get('date_to', '').strip()
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Apply Account filter
        account_id = self.request.GET.get('account', '').strip()
        if account_id and account_id != 'all':
            qs = qs.filter(account_id=account_id)

        # Apply Transaction Type filter
        activity_type = self.request.GET.get('type', '').strip()
        if activity_type and activity_type != 'all':
            qs = qs.filter(activity_type=activity_type)

        # Apply Category name filter
        category = self.request.GET.get('category', '').strip()
        if category and category != 'all':
            qs = qs.filter(category_name__iexact=category)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Expose accounts for dropdown filter
        context['accounts'] = Account.objects.filter(user=self.request.user)
        # Expose unique category names for dropdown filter
        categories = list(TransactionHistory.objects.filter(user=self.request.user)\
            .values_list('category_name', flat=True).distinct().order_by('category_name'))
        # Filter out empty or duplicate category names
        context['categories'] = [c for c in categories if c]
        # Expose activity choices
        context['activity_types'] = TransactionHistory.ACTIVITY_CHOICES
        
        # Maintain query params in pagination links
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_string'] = query_params.urlencode()
        
        return context

class TransactionHistoryDetailView(LoginRequiredMixin, DetailView):
    model = TransactionHistory
    template_name = 'transactions/transaction_history_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return TransactionHistory.objects.filter(user=self.request.user)