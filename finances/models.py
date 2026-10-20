from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class Category(models.Model):
    TYPE_CHOICES = (
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    )

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='EXPENSE')
    icon = models.CharField(max_length=50, default='tag', help_text="Lucide icon name (e.g. utensils, shopping-bag, briefcase)")
    color = models.CharField(max_length=20, default='#10b981', help_text="Hex color code for tags and charts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='custom_categories')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        permissions = [
            ("can_manage_shared_categories", "Can create and manage shared global categories"),
        ]

    def __str__(self):
        scope = "Shared" if self.user is None else f"User: {self.user.username}"
        return f"{self.name} ({self.get_category_type_display()} - {scope})"


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='EXPENSE')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-date', '-created_at']
        permissions = [
            ("can_export_transactions", "Can export transaction data to CSV or JSON"),
            ("can_audit_all_transactions", "Can audit transactions across users (Auditor/Manager)"),
        ]

    def __str__(self):
        return f"{self.transaction_type}: {self.description} ({self.amount})"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Monthly budget ceiling")
    period_month = models.PositiveSmallIntegerField(default=timezone.now().month)
    period_year = models.PositiveSmallIntegerField(default=timezone.now().year)
    alert_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('80.0'),
        help_text="Percentage threshold (e.g. 80.00%) to trigger warning"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'category', 'period_month', 'period_year')
        ordering = ['-period_year', '-period_month', 'category__name']
        permissions = [
            ("can_override_budget_limit", "Can override budget spending warnings"),
            ("can_view_department_budgets", "Can view all team/department budgets"),
        ]

    def __str__(self):
        return f"Budget for {self.category.name}: {self.amount} ({self.period_month}/{self.period_year})"


class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    title = models.CharField(max_length=150)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    target_date = models.DateField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='savings_goals')
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['is_completed', 'target_date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.current_amount} / {self.target_amount}"


class SavingsContribution(models.Model):
    goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Contribution of {self.amount} to {self.goal.title}"


class NotificationReminder(models.Model):
    LEVEL_CHOICES = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Critical / Danger'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        level_str = str(self.level).upper()
        return f"[{level_str}] {self.title} for {self.user.username}"
