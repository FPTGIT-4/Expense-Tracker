import datetime
from django.utils import timezone
from .models import RecurringTransaction, GeneratedOccurrence, add_months
from income.models import Income
from expenses.models import Expense
from companies.models import CompanyIncome, CompanyExpense

def get_expected_occurrences(recur, today=None):
    if today is None:
        today = timezone.localdate()
    
    limit_date = min(today, recur.end_date) if recur.end_date else today
    if recur.start_date > limit_date:
        return []
        
    dates = []
    curr = recur.start_date
    i = 0
    while curr <= limit_date:
        dates.append(curr)
        i += 1
        if recur.frequency == 'Daily':
            curr = recur.start_date + datetime.timedelta(days=i)
        elif recur.frequency == 'Weekly':
            curr = recur.start_date + datetime.timedelta(weeks=i)
        elif recur.frequency == 'Monthly':
            curr = add_months(recur.start_date, i)
        elif recur.frequency == 'Quarterly':
            curr = add_months(recur.start_date, i * 3)
        elif recur.frequency == 'Yearly':
            curr = add_months(recur.start_date, i * 12)
    return dates

def generate_recurring_transactions(user):
    active_recurrences = RecurringTransaction.objects.filter(user=user, status='Active')
    today = timezone.localdate()
    
    for recur in active_recurrences:
        expected_dates = get_expected_occurrences(recur, today)
        for date in expected_dates:
            # Check if this date occurrence has already been generated
            if not GeneratedOccurrence.objects.filter(recurring_transaction=recur, occurrence_date=date).exists():
                income_obj = None
                expense_obj = None
                comp_income_obj = None
                comp_expense_obj = None
                
                # Check if it goes to business/company account or personal
                if recur.company_account_id:
                    if recur.transaction_type == 'Income':
                        comp_income_obj = CompanyIncome.objects.create(
                            company_account=recur.company_account,
                            amount=recur.amount,
                            source=recur.name,
                            date=date,
                            description=recur.notes
                        )
                    else:
                        comp_expense_obj = CompanyExpense.objects.create(
                            company_account=recur.company_account,
                            name=recur.name,
                            amount=recur.amount,
                            category=recur.category,
                            date=date,
                            description=recur.notes
                        )
                else:
                    if recur.transaction_type == 'Income':
                        income_obj = Income.objects.create(
                            user=user,
                            account=recur.account,
                            amount=recur.amount,
                            source=recur.category.name[:50],
                            date=date,
                            description=recur.notes
                        )
                    else:
                        expense_obj = Expense.objects.create(
                            user=user,
                            account=recur.account,
                            name=recur.name,
                            amount=recur.amount,
                            category=recur.category,
                            date=date,
                            description=recur.notes
                        )
                
                # Create history log
                GeneratedOccurrence.objects.create(
                    recurring_transaction=recur,
                    occurrence_date=date,
                    income=income_obj,
                    expense=expense_obj,
                    company_income=comp_income_obj,
                    company_expense=comp_expense_obj
                )
