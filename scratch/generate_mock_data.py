import os
import sys
import django
import datetime
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from categories.models import Category, Label
from accounts.models import Account, AccountTransfer
from income.models import Income
from expenses.models import Expense
from budgets.models import Budget
from goals.models import Goal
from debts.models import Debt, Repayment
from companies.models import CompanyAccount, CompanyIncome, CompanyExpense
from recurrences.models import RecurringTransaction, GeneratedOccurrence

def generate_data():
    username = 'FAYIZPT'
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"User '{username}' does not exist.")
        return

    print(f"Generating 3 months of sample data for user '{username}'...")

    # Clear existing data first (to avoid duplicates or conflicts)
    Income.objects.filter(user=user).delete()
    Expense.objects.filter(user=user).delete()
    AccountTransfer.objects.filter(user=user).delete()
    Budget.objects.filter(user=user).delete()
    Goal.objects.filter(user=user).delete()
    Repayment.objects.filter(debt__user=user).delete()
    Debt.objects.filter(user=user).delete()
    CompanyIncome.objects.filter(company_account__user=user).delete()
    CompanyExpense.objects.filter(company_account__user=user).delete()
    CompanyAccount.objects.filter(user=user).delete()
    GeneratedOccurrence.objects.filter(recurring_transaction__user=user).delete()
    RecurringTransaction.objects.filter(user=user).delete()
    Category.objects.filter(user=user).delete()
    Label.objects.filter(user=user).delete()
    Account.objects.filter(user=user).exclude(name='Cash').delete()

    # Reset Cash account balance
    cash_acc = Account.objects.filter(user=user, name='Cash').first()
    if cash_acc:
        cash_acc.initial_balance = Decimal('150.00')
        cash_acc.save()
    else:
        cash_acc = Account.objects.create(
            user=user,
            name='Cash',
            account_type='Cash',
            initial_balance=Decimal('150.00'),
            minimum_balance=Decimal('20.00')
        )

    # 1. Create Categories
    categories = {}
    cat_specs = [
        ('Food', 'Groceries, dining out, and snacks'),
        ('Transport', 'Fuel, public transit, and taxi/rideshare'),
        ('Utilities', 'Electricity, water, internet, and phone bills'),
        ('Rent', 'Monthly apartment rent payments'),
        ('Entertainment', 'Movies, music, subscriptions, and sports'),
        ('Shopping', 'Clothes, electronics, and personal items'),
        ('Healthcare', 'Doctor visits, medicines, and insurance')
    ]
    for name, desc in cat_specs:
        cat = Category.objects.create(user=user, name=name, description=desc)
        categories[name] = cat

    # 2. Create Labels
    labels = {}
    label_specs = [
        ('Personal', '#10b981'),
        ('Work', '#6366f1'),
        ('Essential', '#3b82f6'),
        ('Optional', '#f59e0b')
    ]
    for name, color in label_specs:
        lbl = Label.objects.create(user=user, name=name, color=color)
        labels[name] = lbl

    # 3. Create Accounts
    checking_acc = Account.objects.create(
        user=user,
        name='Checking Account',
        account_type='Bank Account',
        initial_balance=Decimal('3200.00'),
        minimum_balance=Decimal('500.00'),
        notes='Primary salary deposit account'
    )
    
    savings_acc = Account.objects.create(
        user=user,
        name='Savings Account',
        account_type='Bank Account',
        initial_balance=Decimal('8500.00'),
        minimum_balance=Decimal('1000.00'),
        notes='Emergency fund savings'
    )

    credit_card = Account.objects.create(
        user=user,
        name='Amex Gold',
        account_type='Credit Card',
        initial_balance=Decimal('0.00'),
        minimum_balance=Decimal('0.00'),
        notes='Credit card with reward points'
    )

    # 4. Create Budgets (April, May, June 2026)
    months_years = [(4, 2026), (5, 2026), (6, 2026)]
    for m, y in months_years:
        Budget.objects.create(user=user, category=categories['Food'], budget_amount=Decimal('450.00'), month=m, year=y, notes='Monthly food budget')
        Budget.objects.create(user=user, category=categories['Transport'], budget_amount=Decimal('150.00'), month=m, year=y, notes='Monthly commute and fuel')
        Budget.objects.create(user=user, category=categories['Entertainment'], budget_amount=Decimal('100.00'), month=m, year=y, notes='Subscription and events budget')
        Budget.objects.create(user=user, category=categories['Shopping'], budget_amount=Decimal('200.00'), month=m, year=y, notes='Clothes and gear')

    # 5. Create Goals
    Goal.objects.create(user=user, name='Europe Trip Summer', target_amount=Decimal('4000.00'), current_amount=Decimal('1800.00'), target_date=datetime.date(2026, 12, 1), description='Savings for a 2-week vacation in Europe.')
    Goal.objects.create(user=user, name='Emergency reserve', target_amount=Decimal('10000.00'), current_amount=Decimal('8500.00'), target_date=datetime.date(2027, 6, 1), description='6 months living expenses reserve.')

    # 6. Create Debts
    debt_friend = Debt.objects.create(
        user=user,
        person_name='John Doe',
        debt_type='Borrowed',
        amount=Decimal('300.00'),
        date=datetime.date(2026, 4, 15),
        due_date=datetime.date(2026, 7, 15),
        notes='Support for laptop upgrade repair costs'
    )
    
    debt_sister = Debt.objects.create(
        user=user,
        person_name='Jane Smith',
        debt_type='Lent',
        amount=Decimal('150.00'),
        date=datetime.date(2026, 5, 10),
        due_date=datetime.date(2026, 6, 10),
        notes='Lent money for textbook purchases'
    )

    # 7. Create Company Account
    company_acc = CompanyAccount.objects.create(
        user=user,
        name='Fayiz Consulting Corp',
        description='Freelance software consulting business finances',
        opening_balance=Decimal('5000.00'),
        created_date=datetime.date(2026, 1, 1),
        status='ACTIVE'
    )

    # Helper function to assign labels to transaction
    def add_txn_labels(txn, label_names):
        for name in label_names:
            if name in labels:
                txn.labels.add(labels[name])

    # ------------------ Month 1: April 2026 ------------------
    print("Populating April 2026 data...")
    # Income
    inc_salary_apr = Income.objects.create(user=user, account=checking_acc, amount=Decimal('3500.00'), source='Salary', date=datetime.date(2026, 4, 1), description='Monthly software engineer salary')
    add_txn_labels(inc_salary_apr, ['Work', 'Essential'])
    
    inc_side_apr = Income.objects.create(user=user, account=checking_acc, amount=Decimal('450.00'), source='Freelancing', date=datetime.date(2026, 4, 15), description='Landing page contract payment')
    add_txn_labels(inc_side_apr, ['Work'])

    # Transfers
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=savings_acc, amount=Decimal('500.00'), transfer_date=datetime.date(2026, 4, 2), note='Monthly savings automated deposit')
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=cash_acc, amount=Decimal('150.00'), transfer_date=datetime.date(2026, 4, 3), note='ATM cash withdrawal')

    # Expenses
    exp_rent_apr = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('1200.00'), name='Rent Payment', date=datetime.date(2026, 4, 1), category=categories['Rent'], description='April rent charge')
    add_txn_labels(exp_rent_apr, ['Essential'])

    exp_util_apr = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('180.00'), name='Utilities Bill', date=datetime.date(2026, 4, 5), category=categories['Utilities'], description='Power and high-speed internet bills combined')
    add_txn_labels(exp_util_apr, ['Essential'])

    exp_food1_apr = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('82.50'), name='Costco Groceries', date=datetime.date(2026, 4, 3), category=categories['Food'], description='Weekly groceries refill')
    add_txn_labels(exp_food1_apr, ['Essential', 'Personal'])

    exp_food2_apr = Expense.objects.create(user=user, account=cash_acc, amount=Decimal('32.00'), name='Subway Lunch', date=datetime.date(2026, 4, 8), category=categories['Food'])
    add_txn_labels(exp_food2_apr, ['Personal'])

    exp_ent1_apr = Expense.objects.create(user=user, account=credit_card, amount=Decimal('15.99'), name='Netflix Subscription', date=datetime.date(2026, 4, 10), category=categories['Entertainment'], description='Monthly Netflix Premium Plan')
    add_txn_labels(exp_ent1_apr, ['Optional', 'Personal'])

    exp_trans1_apr = Expense.objects.create(user=user, account=credit_card, amount=Decimal('45.00'), name='Shell Gas', date=datetime.date(2026, 4, 12), category=categories['Transport'])
    add_txn_labels(exp_trans1_apr, ['Essential'])

    exp_shop1_apr = Expense.objects.create(user=user, account=credit_card, amount=Decimal('79.00'), name='Amazon Kindle Book', date=datetime.date(2026, 4, 16), category=categories['Shopping'])
    add_txn_labels(exp_shop1_apr, ['Optional'])

    exp_food3_apr = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('90.20'), name='Whole Foods Market', date=datetime.date(2026, 4, 18), category=categories['Food'])
    add_txn_labels(exp_food3_apr, ['Essential'])

    exp_health_apr = Expense.objects.create(user=user, account=cash_acc, amount=Decimal('25.00'), name='CVS Prescription', date=datetime.date(2026, 4, 20), category=categories['Healthcare'])
    add_txn_labels(exp_health_apr, ['Essential'])

    # Credit card settlement transfer
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=credit_card, amount=Decimal('139.99'), transfer_date=datetime.date(2026, 4, 28), note='Autopay Credit Card Statement Clearance')

    # Company April Transactions
    CompanyIncome.objects.create(company_account=company_acc, amount=Decimal('2500.00'), source='Acme Corp Retainer', date=datetime.date(2026, 4, 10), description='April consulting retainer invoice #104')
    CompanyExpense.objects.create(company_account=company_acc, name='AWS Server Fee', amount=Decimal('110.00'), category=categories['Utilities'], date=datetime.date(2026, 4, 5))
    CompanyExpense.objects.create(company_account=company_acc, name='Coworking Desk Space Rent', amount=Decimal('250.00'), category=categories['Rent'], date=datetime.date(2026, 4, 1))

    # ------------------ Month 2: May 2026 ------------------
    print("Populating May 2026 data...")
    # Income
    inc_salary_may = Income.objects.create(user=user, account=checking_acc, amount=Decimal('3500.00'), source='Salary', date=datetime.date(2026, 5, 1), description='Monthly software engineer salary')
    add_txn_labels(inc_salary_may, ['Work', 'Essential'])

    # Transfers
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=savings_acc, amount=Decimal('500.00'), transfer_date=datetime.date(2026, 5, 2), note='Monthly savings automated deposit')
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=cash_acc, amount=Decimal('150.00'), transfer_date=datetime.date(2026, 5, 3), note='ATM cash withdrawal')

    # Expenses
    exp_rent_may = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('1200.00'), name='Rent Payment', date=datetime.date(2026, 5, 1), category=categories['Rent'], description='May rent charge')
    add_txn_labels(exp_rent_may, ['Essential'])

    exp_util_may = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('175.40'), name='Utilities Bill', date=datetime.date(2026, 5, 5), category=categories['Utilities'])
    add_txn_labels(exp_util_may, ['Essential'])

    exp_food1_may = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('74.80'), name='Kroger Groceries', date=datetime.date(2026, 5, 4), category=categories['Food'])
    add_txn_labels(exp_food1_may, ['Essential'])

    exp_food2_may = Expense.objects.create(user=user, account=credit_card, amount=Decimal('56.00'), name='Olive Garden Dining', date=datetime.date(2026, 5, 9), category=categories['Food'])
    add_txn_labels(exp_food2_may, ['Optional'])

    exp_ent1_may = Expense.objects.create(user=user, account=credit_card, amount=Decimal('15.99'), name='Netflix Subscription', date=datetime.date(2026, 5, 10), category=categories['Entertainment'])
    
    exp_trans1_may = Expense.objects.create(user=user, account=credit_card, amount=Decimal('42.00'), name='Shell Gas', date=datetime.date(2026, 5, 14), category=categories['Transport'])

    exp_shop1_may = Expense.objects.create(user=user, account=credit_card, amount=Decimal('120.00'), name='Nike Shoes', date=datetime.date(2026, 5, 18), category=categories['Shopping'])
    add_txn_labels(exp_shop1_may, ['Optional', 'Personal'])

    exp_food3_may = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('88.50'), name='Trader Joes', date=datetime.date(2026, 5, 22), category=categories['Food'])
    add_txn_labels(exp_food3_may, ['Essential'])

    # Debt payments
    Repayment.objects.create(debt=debt_friend, amount=Decimal('100.00'), date=datetime.date(2026, 5, 10), notes='First laptop repair payback installment')
    Repayment.objects.create(debt=debt_sister, amount=Decimal('50.00'), date=datetime.date(2026, 5, 20), notes='Partial book money payback')

    # Credit card settlement transfer
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=credit_card, amount=Decimal('233.99'), transfer_date=datetime.date(2026, 5, 28), note='Autopay Credit Card Statement Clearance')

    # Company May Transactions
    CompanyIncome.objects.create(company_account=company_acc, amount=Decimal('2500.00'), source='Acme Corp Retainer', date=datetime.date(2026, 5, 10), description='May consulting retainer invoice #105')
    CompanyExpense.objects.create(company_account=company_acc, name='AWS Server Fee', amount=Decimal('122.50'), category=categories['Utilities'], date=datetime.date(2026, 5, 5))
    CompanyExpense.objects.create(company_account=company_acc, name='Coworking Desk Space Rent', amount=Decimal('250.00'), category=categories['Rent'], date=datetime.date(2026, 5, 1))

    # ------------------ Month 3: June 2026 (Ongoing) ------------------
    print("Populating June 2026 data...")
    # Income
    inc_salary_jun = Income.objects.create(user=user, account=checking_acc, amount=Decimal('3500.00'), source='Salary', date=datetime.date(2026, 6, 1), description='Monthly software engineer salary')
    add_txn_labels(inc_salary_jun, ['Work', 'Essential'])

    # Transfers
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=savings_acc, amount=Decimal('500.00'), transfer_date=datetime.date(2026, 6, 2), note='Monthly savings automated deposit')
    AccountTransfer.objects.create(user=user, from_account=checking_acc, to_account=cash_acc, amount=Decimal('100.00'), transfer_date=datetime.date(2026, 6, 3), note='ATM cash withdrawal')

    # Expenses
    exp_rent_jun = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('1200.00'), name='Rent Payment', date=datetime.date(2026, 6, 1), category=categories['Rent'], description='June rent charge')
    add_txn_labels(exp_rent_jun, ['Essential'])

    exp_util_jun = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('165.20'), name='Utilities Bill', date=datetime.date(2026, 6, 5), category=categories['Utilities'])
    add_txn_labels(exp_util_jun, ['Essential'])

    exp_food1_jun = Expense.objects.create(user=user, account=checking_acc, amount=Decimal('92.30'), name='Costco Wholesale', date=datetime.date(2026, 6, 6), category=categories['Food'])
    add_txn_labels(exp_food1_jun, ['Essential'])

    exp_ent1_jun = Expense.objects.create(user=user, account=credit_card, amount=Decimal('15.99'), name='Netflix Subscription', date=datetime.date(2026, 6, 10), category=categories['Entertainment'])

    exp_trans1_jun = Expense.objects.create(user=user, account=credit_card, amount=Decimal('48.00'), name='Exxon Mobil Gas', date=datetime.date(2026, 6, 12), category=categories['Transport'])

    # Debt payments
    Repayment.objects.create(debt=debt_friend, amount=Decimal('100.00'), date=datetime.date(2026, 6, 10), notes='Second laptop repair payback installment')

    # Company June Transactions
    CompanyIncome.objects.create(company_account=company_acc, amount=Decimal('2500.00'), source='Acme Corp Retainer', date=datetime.date(2026, 6, 10), description='June consulting retainer invoice #106')
    CompanyExpense.objects.create(company_account=company_acc, name='AWS Server Fee', amount=Decimal('118.40'), category=categories['Utilities'], date=datetime.date(2026, 6, 5))
    CompanyExpense.objects.create(company_account=company_acc, name='Coworking Desk Space Rent', amount=Decimal('250.00'), category=categories['Rent'], date=datetime.date(2026, 6, 1))

    # ------------------ Recurring Transaction Definition ------------------
    # Let's add a Recurring Gym Membership Transaction
    recur_gym = RecurringTransaction.objects.create(
        user=user,
        name='Gym Membership',
        transaction_type='Expense',
        amount=Decimal('45.00'),
        category=categories['Entertainment'],
        account=credit_card,
        frequency='Monthly',
        start_date=datetime.date(2026, 4, 1),
        notes='Monthly fitness center pass auto-billing',
        status='Active'
    )
    
    # Generate occurrences
    GeneratedOccurrence.objects.create(recurring_transaction=recur_gym, occurrence_date=datetime.date(2026, 4, 1))
    GeneratedOccurrence.objects.create(recurring_transaction=recur_gym, occurrence_date=datetime.date(2026, 5, 1))
    GeneratedOccurrence.objects.create(recurring_transaction=recur_gym, occurrence_date=datetime.date(2026, 6, 1))

    print("Sample data populated successfully!")

if __name__ == '__main__':
    generate_data()
