from decimal import Decimal
import datetime
from django.db.models import Sum
from income.models import Income
from expenses.models import Expense
from categories.models import Category

class ReportDataService:
    @staticmethod
    def get_report_data(user, start_date, end_date):
        # Filtered querysets (transactions strictly within the range)
        incomes = Income.objects.filter(user=user, date__range=(start_date, end_date))
        expenses = Expense.objects.filter(user=user, date__range=(start_date, end_date))

        # Summary calculations within date range
        total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_balance = total_income - total_expenses
        total_transactions = incomes.count() + expenses.count()

        # Category-wise Expense Report (filtered range)
        category_report = []
        if total_expenses > 0:
            category_data = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')
            for item in category_data:
                cat_name = item['category__name'] or 'Uncategorized'
                amount = item['total'] or Decimal('0.00')
                percentage = (amount / total_expenses) * 100
                category_report.append({
                    'name': cat_name,
                    'amount': amount,
                    'percentage': percentage,
                })

        # Income Source Report (filtered range)
        source_report = []
        source_data = incomes.values('source').annotate(total=Sum('amount')).order_by('-total')
        for item in source_data:
            source_report.append({
                'source': item['source'],
                'amount': item['total'] or Decimal('0.00'),
            })

        # Recent Transactions list (filtered range)
        transactions = []
        for inc in incomes:
            transactions.append({
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'category_or_source': inc.source,
                'amount': inc.amount,
                'description': inc.description,
            })
        for exp in expenses:
            transactions.append({
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'amount': exp.amount,
                'description': exp.description,
            })
        # Sort transaction history descending
        transactions.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)

        # Monthly summary (All time for user, grouped by calendar month)
        all_incomes = Income.objects.filter(user=user)
        all_expenses = Expense.objects.filter(user=user)

        monthly_data = {}
        for inc in all_incomes:
            key = (inc.date.year, inc.date.month)
            if key not in monthly_data:
                monthly_data[key] = {'income': Decimal('0.00'), 'expense': Decimal('0.00')}
            monthly_data[key]['income'] += inc.amount

        for exp in all_expenses:
            key = (exp.date.year, exp.date.month)
            if key not in monthly_data:
                monthly_data[key] = {'income': Decimal('0.00'), 'expense': Decimal('0.00')}
            monthly_data[key]['expense'] += exp.amount

        monthly_summary = []
        for key, values in monthly_data.items():
            year, month = key
            month_date = datetime.date(year, month, 1)
            inc_val = values['income']
            exp_val = values['expense']
            monthly_summary.append({
                'month_date': month_date,
                'income': inc_val,
                'expense': exp_val,
                'balance': inc_val - exp_val,
            })
        # Sort by month date descending (newest first)
        monthly_summary.sort(key=lambda x: x['month_date'], reverse=True)

        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'current_balance': current_balance,
            'total_transactions': total_transactions,
            'category_report': category_report,
            'source_report': source_report,
            'recent_transactions': transactions,
            'monthly_summary': monthly_summary,
        }
