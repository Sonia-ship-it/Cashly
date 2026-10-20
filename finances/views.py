import csv
import json
import calendar
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Q

from accounts.permissions import get_user_role
from .models import Transaction, Budget, SavingsGoal, SavingsContribution, NotificationReminder, Category
from .forms import TransactionForm, BudgetForm, SavingsGoalForm, SavingsContributionForm, CategoryForm
from .services.calculator import (
    compute_financial_summary,
    compute_budget_details,
    compute_savings_goal_details,
    compute_category_breakdown,
    to_float,
)
from .services.alerts import check_and_generate_alerts


@login_required
def dashboard_view(request):
    user = request.user
    now = timezone.now()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))

    # Calculate financial summary powered by PyBasics Kit
    summary = compute_financial_summary(user, month=month, year=year)

    # Active budgets
    budgets_qs = Budget.objects.filter(user=user, period_month=month, period_year=year)
    budget_items = [compute_budget_details(b) for b in budgets_qs]

    # Active savings goals
    goals_qs = SavingsGoal.objects.filter(user=user, is_completed=False)[:4]
    goal_items = [compute_savings_goal_details(g) for g in goals_qs]

    # Recent transactions
    recent_transactions = Transaction.objects.filter(user=user).select_related('category')[:8]

    # Unread notifications
    notifications = NotificationReminder.objects.filter(user=user, is_read=False)[:5]

    # Category breakdown for chart
    expense_breakdown = compute_category_breakdown(user, month=month, year=year, tx_type='EXPENSE')

    # Monthly trends for chart (last 6 months)
    trends = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        m_name = calendar.month_abbr[m]
        tx_m = Transaction.objects.filter(user=user, date__year=y, date__month=m)
        inc = to_float(tx_m.filter(transaction_type='INCOME').aggregate(total=Sum('amount'))['total'])
        exp = to_float(tx_m.filter(transaction_type='EXPENSE').aggregate(total=Sum('amount'))['total'])
        trends.append({'month': f"{m_name} {y}", 'income': inc, 'expenses': exp})

    # Currency format
    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')
    role_name = get_user_role(user)

    context = {
        'summary': summary,
        'budgets': budget_items,
        'goals': goal_items,
        'recent_transactions': recent_transactions,
        'notifications': notifications,
        'expense_breakdown': expense_breakdown,
        'trends': trends,
        'trends_json': json.dumps(trends),
        'breakdown_json': json.dumps(expense_breakdown['items']),
        'currency': currency,
        'role_name': role_name,
        'current_month': month,
        'current_year': year,
        'quick_form': TransactionForm(user=user),
    }
    return render(request, 'finances/dashboard.html', context)


@login_required
def transactions_list_view(request):
    user = request.user
    can_audit = user.has_perm('finances.can_audit_all_transactions')
    view_all = request.GET.get('audit_mode') == '1' and can_audit

    qs = Transaction.objects.all() if view_all else Transaction.objects.filter(user=user)
    qs = qs.select_related('category', 'user')

    # Filters
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(Q(description__icontains=search) | Q(notes__icontains=search) | Q(category__name__icontains=search))

    tx_type = request.GET.get('type')
    if tx_type in ['INCOME', 'EXPENSE']:
        qs = qs.filter(transaction_type=tx_type)

    cat_id = request.GET.get('category')
    if cat_id:
        qs = qs.filter(category_id=cat_id)

    start_date = request.GET.get('start_date')
    if start_date:
        qs = qs.filter(date__gte=start_date)

    end_date = request.GET.get('end_date')
    if end_date:
        qs = qs.filter(date__lte=end_date)

    # Export to CSV check
    if request.GET.get('export') == 'csv':
        if not (user.has_perm('finances.can_export_transactions') or user.is_superuser):
            raise PermissionDenied("You do not have permission to export transactions.")

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="cashly_transactions_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Category', 'Description', 'Amount', 'User', 'Notes'])
        for t in qs:
            writer.writerow([
                t.date,
                t.transaction_type,
                t.category.name if t.category else 'Uncategorized',
                t.description,
                t.amount,
                t.user.username,
                t.notes,
            ])
        return response

    # Pagination
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(Q(user=user) | Q(user__isnull=True)).order_by('name')
    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'currency': currency,
        'search': search,
        'tx_type': tx_type,
        'cat_id': cat_id,
        'start_date': start_date,
        'end_date': end_date,
        'can_audit': can_audit,
        'view_all': view_all,
        'role_name': get_user_role(user),
    }
    return render(request, 'finances/transactions_list.html', context)


@login_required
def transaction_create_view(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.user = request.user
            tx.save()
            check_and_generate_alerts(request.user)
            messages.success(request, f"Transaction '{tx.description}' successfully added!")
            return redirect('finances:transactions')
    else:
        form = TransactionForm(user=request.user)

    currency = getattr(getattr(request.user, 'profile', None), 'currency_code', 'RWF')
    return render(request, 'finances/transaction_form.html', {'form': form, 'title': 'Record New Transaction', 'currency': currency})


@login_required
def transactions_batch_create_view(request):
    """
    Allows user to record multiple transactions simultaneously
    in a clean spreadsheet-like batch entry form.
    """
    user = request.user
    categories = Category.objects.filter(
        Q(user=user) | Q(user__isnull=True)
    ).order_by('category_type', 'name')

    if request.method == 'POST':
        dates = request.POST.getlist('date[]')
        tx_types = request.POST.getlist('transaction_type[]')
        cat_ids = request.POST.getlist('category[]')
        descriptions = request.POST.getlist('description[]')
        amounts = request.POST.getlist('amount[]')
        notes_list = request.POST.getlist('notes[]')

        saved_count = 0
        now_date = timezone.now().date()

        for i in range(len(amounts)):
            amt_raw = amounts[i].strip() if i < len(amounts) else ''
            desc_raw = descriptions[i].strip() if i < len(descriptions) else ''
            if not amt_raw or not desc_raw:
                continue

            try:
                amt = Decimal(amt_raw)
                if amt <= 0:
                    continue

                d_str = dates[i].strip() if i < len(dates) else ''
                t_date = datetime.strptime(d_str, '%Y-%m-%d').date() if d_str else now_date

                t_type = tx_types[i].strip() if i < len(tx_types) else 'EXPENSE'
                if t_type not in ['INCOME', 'EXPENSE']:
                    t_type = 'EXPENSE'

                c_id = cat_ids[i].strip() if i < len(cat_ids) else None
                cat = Category.objects.filter(id=c_id).first() if c_id else None

                notes = notes_list[i].strip() if i < len(notes_list) else ''

                Transaction.objects.create(
                    user=user,
                    date=t_date,
                    transaction_type=t_type,
                    category=cat,
                    description=desc_raw,
                    amount=amt,
                    notes=notes,
                )
                saved_count += 1
            except Exception:
                continue

        if saved_count > 0:
            check_and_generate_alerts(user)
            messages.success(request, f"Successfully recorded {saved_count} transactions!")
            return redirect('finances:transactions')
        else:
            messages.warning(request, "No valid transactions were entered. Please fill in Amount and Description.")

    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')
    today_str = timezone.now().strftime('%Y-%m-%d')

    context = {
        'categories': categories,
        'currency': currency,
        'today_str': today_str,
        'role_name': get_user_role(user),
    }
    return render(request, 'finances/transactions_batch_form.html', context)


@login_required
def transaction_update_view(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    # Check permissions & ownership
    if tx.user != request.user and not request.user.has_perm('finances.can_audit_all_transactions') and not request.user.is_superuser:
        raise PermissionDenied("You cannot edit this transaction.")

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=tx, user=request.user)
        if form.is_valid():
            form.save()
            check_and_generate_alerts(request.user)
            messages.success(request, "Transaction updated successfully.")
            return redirect('finances:transactions')
    else:
        form = TransactionForm(instance=tx, user=request.user)

    return render(request, 'finances/transaction_form.html', {'form': form, 'title': 'Edit Transaction', 'tx': tx})


@login_required
def transaction_delete_view(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    if tx.user != request.user and not request.user.is_superuser:
        raise PermissionDenied("You cannot delete this transaction.")

    if request.method == 'POST':
        tx.delete()
        check_and_generate_alerts(request.user)
        messages.success(request, "Transaction deleted successfully.")
        return redirect('finances:transactions')

    return render(request, 'finances/confirm_delete.html', {'item': tx, 'type': 'Transaction'})


@login_required
def budgets_list_view(request):
    user = request.user
    now = timezone.now()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))

    budgets_qs = Budget.objects.filter(user=user, period_month=month, period_year=year).select_related('category')
    budget_items = [compute_budget_details(b) for b in budgets_qs]

    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')

    context = {
        'budgets': budget_items,
        'current_month': month,
        'current_year': year,
        'month_name': calendar.month_name[month],
        'currency': currency,
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'role_name': get_user_role(user),
    }
    return render(request, 'finances/budgets_list.html', context)


@login_required
def budget_create_view(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            # Check for existing budget for same category/month/year
            existing = Budget.objects.filter(
                user=request.user,
                category=budget.category,
                period_month=budget.period_month,
                period_year=budget.period_year
            ).first()
            if existing:
                existing.amount = budget.amount
                existing.alert_threshold = budget.alert_threshold
                existing.save()
                messages.info(request, f"Updated existing budget for {budget.category.name}.")
            else:
                budget.save()
                messages.success(request, f"Budget for {budget.category.name} created successfully!")
            check_and_generate_alerts(request.user)
            from django.urls import reverse
            return redirect(f"{reverse('finances:budgets')}?month={budget.period_month}&year={budget.period_year}")
    else:
        form = BudgetForm(user=request.user)

    return render(request, 'finances/budget_form.html', {'form': form, 'title': 'Create Budget'})


@login_required
def budgets_bulk_setup_view(request):
    """
    Allows user to configure spending ceilings for all categories simultaneously
    in a single comprehensive monthly budget sheet.
    """
    user = request.user
    now = timezone.now()
    month = int(request.GET.get('month', request.POST.get('month', now.month)))
    year = int(request.GET.get('year', request.POST.get('year', now.year)))

    categories = Category.objects.filter(
        Q(user=user) | Q(user__isnull=True),
        category_type='EXPENSE'
    ).order_by('name')

    existing_budgets = {
        b.category_id: b
        for b in Budget.objects.filter(user=user, period_month=month, period_year=year)
    }

    if request.method == 'POST':
        saved_count = 0
        for cat in categories:
            amt_str = request.POST.get(f'amount_{cat.id}', '').strip()
            thresh_str = request.POST.get(f'threshold_{cat.id}', '80').strip()

            if amt_str:
                try:
                    amt = Decimal(amt_str)
                    thresh = Decimal(thresh_str) if thresh_str else Decimal('80.0')

                    if amt > 0:
                        b, created = Budget.objects.get_or_create(
                            user=user,
                            category=cat,
                            period_month=month,
                            period_year=year,
                            defaults={'amount': amt, 'alert_threshold': thresh}
                        )
                        if not created:
                            b.amount = amt
                            b.alert_threshold = thresh
                            b.save()
                        saved_count += 1
                    else:
                        Budget.objects.filter(user=user, category=cat, period_month=month, period_year=year).delete()
                except Exception:
                    pass
            else:
                if request.POST.get(f'clear_{cat.id}') == '1':
                    Budget.objects.filter(user=user, category=cat, period_month=month, period_year=year).delete()

        check_and_generate_alerts(user)
        messages.success(request, f"Saved monthly budget plan for {calendar.month_name[month]} {year} ({saved_count} categories configured)!")
        from django.urls import reverse
        return redirect(f"{reverse('finances:budgets')}?month={month}&year={year}")

    # Build category rows
    category_rows = []
    total_planned = Decimal('0.0')
    for cat in categories:
        b = existing_budgets.get(cat.id)
        current_amount = b.amount if b else ''
        current_threshold = b.alert_threshold if b else Decimal('80.0')
        if b and b.amount:
            total_planned += b.amount
        category_rows.append({
            'category': cat,
            'budget': b,
            'amount': current_amount,
            'threshold': current_threshold,
        })

    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')

    context = {
        'category_rows': category_rows,
        'current_month': month,
        'current_year': year,
        'month_name': calendar.month_name[month],
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'currency': currency,
        'total_planned': total_planned,
        'role_name': get_user_role(user),
    }
    return render(request, 'finances/budgets_bulk_setup.html', context)


@login_required
def budget_delete_view(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    if budget.user != request.user and not request.user.is_superuser:
        raise PermissionDenied("You cannot delete this budget.")

    if request.method == 'POST':
        budget.delete()
        messages.success(request, "Budget deleted.")
        return redirect('finances:budgets')

    return render(request, 'finances/confirm_delete.html', {'item': budget, 'type': 'Budget'})


@login_required
def savings_goals_list_view(request):
    user = request.user
    goals_qs = SavingsGoal.objects.filter(user=user)
    goal_items = [compute_savings_goal_details(g) for g in goals_qs]

    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')

    context = {
        'goals': goal_items,
        'currency': currency,
        'role_name': get_user_role(user),
    }
    return render(request, 'finances/savings_list.html', context)


@login_required
def savings_goal_create_view(request):
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f"Savings Goal '{goal.title}' created!")
            return redirect('finances:savings')
    else:
        form = SavingsGoalForm()

    return render(request, 'finances/savings_form.html', {'form': form, 'title': 'Create Savings Goal'})


@login_required
def savings_goal_contribute_view(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SavingsContributionForm(request.POST)
        if form.is_valid():
            contrib = form.save(commit=False)
            contrib.goal = goal
            contrib.save()

            goal.current_amount += contrib.amount
            if goal.current_amount >= goal.target_amount:
                goal.is_completed = True
            goal.save()

            check_and_generate_alerts(request.user)
            messages.success(request, f"Contributed {contrib.amount} to '{goal.title}'!")
            return redirect('finances:savings')
    else:
        form = SavingsContributionForm()

    return render(request, 'finances/contribution_form.html', {'form': form, 'goal': goal})


@login_required
def savings_goal_delete_view(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, "Savings goal deleted.")
        return redirect('finances:savings')
    return render(request, 'finances/confirm_delete.html', {'item': goal, 'type': 'Savings Goal'})


@login_required
def reports_view(request):
    user = request.user
    now = timezone.now()
    year = int(request.GET.get('year', now.year))

    # Calculate 12-month summary for the year
    monthly_data = []
    total_income_year = 0.0
    total_expense_year = 0.0

    for m in range(1, 13):
        summary = compute_financial_summary(user, month=m, year=year)
        monthly_data.append(summary)
        total_income_year += summary['income']
        total_expense_year += summary['expenses']

    # PyBasics Kit overall calculations
    from pybasics_kit import calculate_balance, calculate_savings, calculate_savings_rate
    year_balance = float(calculate_balance(income=total_income_year, expenses=total_expense_year))
    year_savings = float(calculate_savings(income=total_income_year, expenses=total_expense_year))
    year_savings_rate = 0.0
    if total_income_year > 0:
        try:
            year_savings_rate = round(float(calculate_savings_rate(income=total_income_year, savings=year_savings)), 1)
        except Exception:
            year_savings_rate = 0.0

    # Expense breakdown for entire year
    txs_year = Transaction.objects.filter(user=user, date__year=year, transaction_type='EXPENSE')
    year_categories = compute_category_breakdown(user, month=now.month, year=year, tx_type='EXPENSE')

    currency = getattr(getattr(user, 'profile', None), 'currency_code', 'RWF')

    context = {
        'year': year,
        'monthly_data': monthly_data,
        'total_income_year': total_income_year,
        'total_expense_year': total_expense_year,
        'year_balance': year_balance,
        'year_savings': year_savings,
        'year_savings_rate': year_savings_rate,
        'year_categories': year_categories,
        'monthly_data_json': json.dumps([{
            'month': d['month_name'],
            'income': d['income'],
            'expenses': d['expenses'],
            'balance': d['balance'],
        } for d in monthly_data]),
        'currency': currency,
        'role_name': get_user_role(user),
    }
    return render(request, 'finances/reports.html', context)


@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(NotificationReminder, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect(notif.link or 'finances:dashboard')


@login_required
def mark_all_notifications_read(request):
    NotificationReminder.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'finances:dashboard')


@login_required
def notification_delete_view(request, pk):
    notif = get_object_or_404(NotificationReminder, pk=pk, user=request.user)
    notif.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'finances:dashboard')


@login_required
def notifications_clear_all_view(request):
    NotificationReminder.objects.filter(user=request.user).delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'finances:dashboard')
