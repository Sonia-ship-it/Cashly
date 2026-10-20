import calendar
from django.utils import timezone
from finances.models import Budget, SavingsGoal, NotificationReminder
from finances.services.calculator import compute_budget_details, compute_savings_goal_details


def check_and_generate_alerts(user):
    """
    Evaluates active budgets and savings goals,
    generating friendly and actionable alerts when thresholds or milestones are met.
    """
    # Evaluate all configured budgets for this user
    budgets = Budget.objects.filter(user=user)

    for budget in budgets:
        details = compute_budget_details(budget)
        spent = details['spent']
        limit = details['limit']
        pct = details['usage_pct']
        cat_name = budget.category.name
        m_name = calendar.month_name[budget.period_month]

        if pct >= 100.0:
            title = f"Budget Exceeded: {cat_name} ({m_name})"
            msg = f"You have spent {spent:,.2f} of your {limit:,.2f} budget ({pct}%) for {m_name}. Consider adjusting expenses in {cat_name}."
            if not NotificationReminder.objects.filter(user=user, title=title, is_read=False).exists():
                NotificationReminder.objects.create(
                    user=user,
                    title=title,
                    message=msg,
                    level='danger',
                    link=f'/budgets/?month={budget.period_month}&year={budget.period_year}'
                )
        elif pct >= float(budget.alert_threshold):
            title = f"Budget Alert: {cat_name} nearing limit ({m_name})"
            msg = f"You have reached {pct}% ({spent:,.2f} of {limit:,.2f}) for your {cat_name} budget in {m_name}."
            if not NotificationReminder.objects.filter(user=user, title=title, is_read=False).exists():
                NotificationReminder.objects.create(
                    user=user,
                    title=title,
                    message=msg,
                    level='warning',
                    link=f'/budgets/?month={budget.period_month}&year={budget.period_year}'
                )

    goals = SavingsGoal.objects.filter(user=user, is_completed=False)
    for goal in goals:
        details = compute_savings_goal_details(goal)
        if details['is_achieved']:
            goal.is_completed = True
            goal.save()
            title = f"Goal Achieved: {goal.title} 🎉"
            msg = f"Congratulations! You reached your savings target of {goal.target_amount:,.2f}."
            if not NotificationReminder.objects.filter(user=user, title=title, is_read=False).exists():
                NotificationReminder.objects.create(
                    user=user,
                    title=title,
                    message=msg,
                    level='success',
                    link='/savings/'
                )
