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
        net_balance = total_income - total_expenses

        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_balance': net_balance,
        }
