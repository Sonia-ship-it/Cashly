from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone

from accounts.permissions import (
    setup_roles_and_permissions,
    assign_user_to_role,
    ROLE_STANDARD_USER,
    ROLE_FINANCIAL_MANAGER,
    ROLE_AUDITOR
)
from finances.models import Category, Transaction, Budget, SavingsGoal, NotificationReminder
from finances.services.calculator import (
    compute_financial_summary,
    compute_budget_details,
    compute_savings_goal_details,
)
from finances.services.alerts import check_and_generate_alerts


class PyBasicsKitIntegrationTests(TestCase):
    def setUp(self):
        setup_roles_and_permissions()
        self.user = User.objects.create_user(username="testuser", password="password123")
        assign_user_to_role(self.user, ROLE_STANDARD_USER)

        self.salary_cat = Category.objects.create(name="Salary", category_type="INCOME")
        self.food_cat = Category.objects.create(name="Food", category_type="EXPENSE")

        # Create transactions
        Transaction.objects.create(
            user=self.user,
            category=self.salary_cat,
            transaction_type="INCOME",
            amount=Decimal("500000.00"),
            date=timezone.now().date(),
            description="Monthly Salary"
        )
        Transaction.objects.create(
            user=self.user,
            category=self.food_cat,
            transaction_type="EXPENSE",
            amount=Decimal("80000.00"),
            date=timezone.now().date(),
            description="Groceries"
        )

    def test_financial_summary_pybasics_calculations(self):
        """Verify that PyBasics Kit functions calculate balance and savings correctly."""
        summary = compute_financial_summary(self.user)
        self.assertEqual(summary['income'], 500000.0)
        self.assertEqual(summary['expenses'], 80000.0)
        # PyBasics Kit: balance = income - expenses
        self.assertEqual(summary['balance'], 420000.0)
        self.assertEqual(summary['savings'], 420000.0)
        # Savings rate = (420000 / 500000) * 100 = 84.0%
        self.assertEqual(summary['savings_rate'], 84.0)

    def test_budget_usage_and_remaining(self):
        """Verify PyBasics Kit budget remaining and usage calculations."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.food_cat,
            amount=Decimal("100000.00"),
            period_month=timezone.now().month,
            period_year=timezone.now().year,
            alert_threshold=Decimal("75.0")
        )

        details = compute_budget_details(budget)
        self.assertEqual(details['spent'], 80000.0)
        self.assertEqual(details['limit'], 100000.0)
        # Remaining: 100,000 - 80,000 = 20,000
        self.assertEqual(details['remaining'], 20000.0)
        # Usage: (80000 / 100000) * 100 = 80.0%
        self.assertEqual(details['usage_pct'], 80.0)
        # Because usage (80%) >= alert_threshold (75%), status should be 'warning'
        self.assertEqual(details['status'], 'warning')

    def test_savings_goal_progress(self):
        """Verify PyBasics Kit savings goal percentage calculation."""
        goal = SavingsGoal.objects.create(
            user=self.user,
            title="Laptop",
            target_amount=Decimal("200000.00"),
            current_amount=Decimal("50000.00")
        )

        details = compute_savings_goal_details(goal)
        # 50,000 / 200,000 * 100 = 25.0%
        self.assertEqual(details['progress_pct'], 25.0)
        self.assertEqual(details['remaining_to_save'], 150000.0)
        self.assertFalse(details['is_achieved'])

    def test_alert_generation(self):
        """Verify automatic generation of budget warning notifications."""
        Budget.objects.create(
            user=self.user,
            category=self.food_cat,
            amount=Decimal("100000.00"),
            period_month=timezone.now().month,
            period_year=timezone.now().year,
            alert_threshold=Decimal("75.0")
        )

        check_and_generate_alerts(self.user)
        self.assertTrue(NotificationReminder.objects.filter(user=self.user, level='warning').exists())


class UserGroupsAndPermissionsTests(TestCase):
    def setUp(self):
        setup_roles_and_permissions()
        self.user1 = User.objects.create_user(username="user1", password="pw1")
        assign_user_to_role(self.user1, ROLE_STANDARD_USER)

        self.user2 = User.objects.create_user(username="user2", password="pw2")
        assign_user_to_role(self.user2, ROLE_STANDARD_USER)

        self.manager = User.objects.create_user(username="mgr", password="pwm")
        assign_user_to_role(self.manager, ROLE_FINANCIAL_MANAGER)

        self.category = Category.objects.create(name="Dining", category_type="EXPENSE")
        self.tx1 = Transaction.objects.create(
            user=self.user1,
            category=self.category,
            transaction_type="EXPENSE",
            amount=Decimal("2500.00"),
            description="User1 Coffee"
        )

    def test_user_cannot_edit_other_user_transaction(self):
        """Verify that user2 cannot edit user1's transaction (ownership security)."""
        client = Client()
        client.login(username="user2", password="pw2")
        response = client.get(reverse('finances:transaction_update', args=[self.tx1.pk]))
        # Should raise PermissionDenied (403)
        self.assertEqual(response.status_code, 403)

    def test_manager_has_export_and_audit_permissions(self):
        """Verify that Financial Manager has custom permissions."""
        self.assertTrue(self.manager.has_perm('finances.can_export_transactions'))
        self.assertTrue(self.manager.has_perm('finances.can_audit_all_transactions'))
        self.assertTrue(self.manager.has_perm('finances.can_manage_shared_categories'))
        self.assertFalse(self.user1.has_perm('finances.can_audit_all_transactions'))
