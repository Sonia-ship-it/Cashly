from decimal import Decimal
import calendar
from django.utils import timezone
from django.db.models import Sum

from pybasics_kit import (
    calculate_balance,
    calculate_total_expenses,
    calculate_savings,
    calculate_savings_rate,
    calculate_budget_remaining,
    calculate_budget_usage,
    calculate_daily_budget,
    calculate_percentage,
    calculate_average,
    calculate_percentage_change,
    split_amount,
    calculate_tax,
)


def to_float(val):
    """Safely convert Decimal or None to float."""
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def compute_financial_summary(user, month=None, year=None):
    """
    Computes a comprehensive financial overview for a given user and period
    using PyBasics Kit calculation functions.
    """
    from finances.models import Transaction, Budget

    now = timezone.now()
    month = month or now.month
    year = year or now.year

    # Current period transactions
    current_txs = Transaction.objects.filter(
        user=user,
        date__year=year,
        date__month=month
    )

    income_sum = to_float(
        current_txs.filter(transaction_type='INCOME').aggregate(total=Sum('amount'))['total']
    )
    expense_sum = to_float(
        current_txs.filter(transaction_type='EXPENSE').aggregate(total=Sum('amount'))['total']
    )

    # PyBasics Kit: balance & savings calculations
    balance = float(calculate_balance(income=income_sum, expenses=expense_sum))
    savings = float(calculate_savings(income=income_sum, expenses=expense_sum))

    savings_rate = 0.0
    if income_sum > 0:
        try:
            savings_rate = float(calculate_savings_rate(income=income_sum, savings=savings))
        except (ValueError, ZeroDivisionError):
            savings_rate = 0.0

    # Total expenses calculated via PyBasics Kit
    total_expenses = float(calculate_total_expenses(expenses=expense_sum))

    # Calculate previous month for trends
    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year

    prev_txs = Transaction.objects.filter(
        user=user,
        date__year=prev_year,
        date__month=prev_month
    )
    prev_income = to_float(
        prev_txs.filter(transaction_type='INCOME').aggregate(total=Sum('amount'))['total']
    )
    prev_expenses = to_float(
        prev_txs.filter(transaction_type='EXPENSE').aggregate(total=Sum('amount'))['total']
    )

    # PyBasics Kit: percentage change
    income_change_pct = 0.0
    if prev_income > 0:
        try:
            income_change_pct = round(float(calculate_percentage_change(old=prev_income, new=income_sum)), 1)
        except Exception:
            income_change_pct = 0.0

    expense_change_pct = 0.0
    if prev_expenses > 0:
        try:
            expense_change_pct = round(float(calculate_percentage_change(old=prev_expenses, new=expense_sum)), 1)
        except Exception:
            expense_change_pct = 0.0

    # Overall Monthly Budget Usage across all user budgets for this period
    user_budgets = Budget.objects.filter(user=user, period_month=month, period_year=year)
    total_budget_limit = to_float(user_budgets.aggregate(total=Sum('amount'))['total'])
    
    overall_budget_usage = 0.0
    overall_budget_remaining = 0.0
    if total_budget_limit > 0:
        try:
            overall_budget_usage = round(float(calculate_budget_usage(spending=expense_sum, budget=total_budget_limit)), 1)
        except Exception:
            overall_budget_usage = 0.0
        try:
            overall_budget_remaining = round(float(calculate_budget_remaining(budget=total_budget_limit, spending=expense_sum)), 2)
        except Exception:
            overall_budget_remaining = 0.0

    # Days in current month and daily budget calculation
    _, num_days = calendar.monthrange(year, month)
    remaining_days = max(1, num_days - now.day + 1) if (year == now.year and month == now.month) else num_days

    daily_spendable = 0.0
    if overall_budget_remaining > 0:
        try:
            daily_spendable = round(float(calculate_daily_budget(remaining=overall_budget_remaining, days=remaining_days)), 2)
        except Exception:
            daily_spendable = 0.0

    return {
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'income': income_sum,
        'expenses': total_expenses,
        'balance': balance,
        'savings': savings,
        'savings_rate': round(savings_rate, 1),
        'income_change_pct': income_change_pct,
        'expense_change_pct': expense_change_pct,
        'total_budget_limit': total_budget_limit,
        'overall_budget_usage': overall_budget_usage,
        'overall_budget_remaining': overall_budget_remaining,
        'daily_spendable': daily_spendable,
        'remaining_days': remaining_days,
    }


def compute_budget_details(budget):
    """
    Calculates detailed metrics for an individual budget item using PyBasics Kit:
    - Amount spent in this category
    - Remaining budget
    - Usage percentage
    - Status (good / warning / exceeded)
    - Daily allowable spending for rest of month
    """
    from finances.models import Transaction

    now = timezone.now()
    budget_limit = to_float(budget.amount)

    # Sum expenses for this user, category, and month/year
    category_expenses = Transaction.objects.filter(
        user=budget.user,
        category=budget.category,
        transaction_type='EXPENSE',
        date__year=budget.period_year,
        date__month=budget.period_month
    ).aggregate(total=Sum('amount'))['total']

    spent = to_float(category_expenses)

    # PyBasics Kit calls
    remaining = float(calculate_budget_remaining(budget=budget_limit, spending=spent))
    
    usage_pct = 0.0
    if budget_limit > 0:
        try:
            usage_pct = round(float(calculate_budget_usage(spending=spent, budget=budget_limit)), 1)
        except (ValueError, ZeroDivisionError):
            usage_pct = 0.0

    # Days remaining calculation
    _, num_days = calendar.monthrange(budget.period_year, budget.period_month)
    if budget.period_year == now.year and budget.period_month == now.month:
        remaining_days = max(1, num_days - now.day + 1)
    else:
        remaining_days = num_days

    daily_allowance = 0.0
    if remaining > 0:
        try:
            daily_allowance = round(float(calculate_daily_budget(remaining=remaining, days=remaining_days)), 2)
        except Exception:
            daily_allowance = 0.0

    # Status classification
    threshold = float(budget.alert_threshold)
    if usage_pct >= 100.0 or remaining < 0:
        status = 'exceeded'
        status_color = 'rose'
    elif usage_pct >= threshold:
        status = 'warning'
        status_color = 'amber'
    else:
        status = 'good'
        status_color = 'emerald'

    return {
        'budget': budget,
        'limit': budget_limit,
        'spent': spent,
        'remaining': remaining,
        'usage_pct': usage_pct,
        'status': status,
        'status_color': status_color,
        'daily_allowance': daily_allowance,
        'remaining_days': remaining_days,
    }


def compute_savings_goal_details(goal):
    """
    Calculates progress and projections for a SavingsGoal using PyBasics Kit:
    - Percentage achieved
    - Remaining amount to save
    """
    target = to_float(goal.target_amount)
    current = to_float(goal.current_amount)

    progress_pct = 0.0
    if target > 0:
        try:
            progress_pct = round(float(calculate_percentage(value=current, total=target)), 1)
        except Exception:
            progress_pct = 0.0

    # Using calculate_budget_remaining for remaining target
    remaining_to_save = float(calculate_budget_remaining(budget=target, spending=current))
    remaining_to_save = max(0.0, remaining_to_save)

    # Days remaining if deadline is set
    days_left = None
    monthly_needed = None
    if goal.target_date:
        delta = goal.target_date - timezone.now().date()
        days_left = delta.days
        if days_left > 0 and remaining_to_save > 0:
            months_left = max(1.0, days_left / 30.0)
            monthly_needed = round(remaining_to_save / months_left, 2)

    return {
        'goal': goal,
        'target': target,
        'current': current,
        'progress_pct': min(100.0, progress_pct),
        'remaining_to_save': remaining_to_save,
        'days_left': days_left,
        'monthly_needed': monthly_needed,
        'is_achieved': current >= target,
    }


def compute_category_breakdown(user, month=None, year=None, tx_type='EXPENSE'):
    """
    Calculates category-wise spending distribution and percentages using PyBasics Kit.
    """
    from finances.models import Transaction

    now = timezone.now()
    month = month or now.month
    year = year or now.year

    txs = Transaction.objects.filter(
        user=user,
        transaction_type=tx_type,
        date__year=year,
        date__month=month
    )

    total_amount = to_float(txs.aggregate(total=Sum('amount'))['total'])

    categories_map = {}
    for tx in txs:
        cat_name = tx.category.name if tx.category else "Uncategorized"
        cat_color = tx.category.color if tx.category else "#94a3b8"
        cat_icon = tx.category.icon if tx.category else "help-circle"
        amt = to_float(tx.amount)
        if cat_name not in categories_map:
            categories_map[cat_name] = {
                'name': cat_name,
                'color': cat_color,
                'icon': cat_icon,
                'total': 0.0,
                'percentage': 0.0,
                'count': 0,
            }
        categories_map[cat_name]['total'] += amt
        categories_map[cat_name]['count'] += 1

    result = []
    for cat_name, item in categories_map.items():
        if total_amount > 0:
            try:
                item['percentage'] = round(float(calculate_percentage(value=item['total'], total=total_amount)), 1)
            except Exception:
                item['percentage'] = 0.0
        result.append(item)

    result.sort(key=lambda x: x['total'], reverse=True)
    return {
        'items': result,
        'total': total_amount,
    }
