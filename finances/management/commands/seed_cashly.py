from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from accounts.permissions import setup_roles_and_permissions, assign_user_to_role, ROLE_STANDARD_USER, ROLE_FINANCIAL_MANAGER
from finances.models import Category, Transaction, Budget, SavingsGoal, SavingsContribution
from finances.services.alerts import check_and_generate_alerts


class Command(BaseCommand):
    help = "Seeds standard categories, user roles & permissions, and demo data for Cashly."

    def handle(self, *args, **options):
        self.stdout.write("Setting up user roles and permissions...")
        setup_roles_and_permissions()

        self.stdout.write("Setting up shared default categories...")
        categories_data = [
            # Income
            ("Salary", "INCOME", "briefcase", "#10b981"),
            ("Freelance & Side Hustle", "INCOME", "laptop", "#34d399"),
            ("Investments & Dividends", "INCOME", "trending-up", "#059669"),
            ("Gifts & Grants", "INCOME", "gift", "#6ee7b7"),
            # Expense
            ("Food & Dining", "EXPENSE", "utensils", "#f59e0b"),
            ("Rent & Housing", "EXPENSE", "home", "#6366f1"),
            ("Transport & Commute", "EXPENSE", "car", "#0ea5e9"),
            ("Utilities & Internet", "EXPENSE", "zap", "#8b5cf6"),
            ("Entertainment & Leisure", "EXPENSE", "film", "#ec4899"),
            ("Health & Wellness", "EXPENSE", "heart-pulse", "#ef4444"),
            ("Shopping & Groceries", "EXPENSE", "shopping-bag", "#14b8a6"),
            ("Education & Books", "EXPENSE", "book-open", "#3b82f6"),
        ]

        cats = {}
        for name, c_type, icon, color in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name,
                user=None,
                defaults={
                    'category_type': c_type,
                    'icon': icon,
                    'color': color,
                }
            )
            cats[name] = cat

        # Create Demo User
        self.stdout.write("Creating demo user 'demo'...")
        demo_user, created = User.objects.get_or_create(username="demo")
        if created or not demo_user.check_password("demo12345"):
            demo_user.set_password("demo12345")
            demo_user.first_name = "Alex"
            demo_user.last_name = "Mugisha"
            demo_user.email = "demo@cashly.local"
            demo_user.save()
        assign_user_to_role(demo_user, ROLE_STANDARD_USER)

        # Create Manager User
        self.stdout.write("Creating demo manager 'manager'...")
        manager_user, created_mgr = User.objects.get_or_create(username="manager")
        if created_mgr or not manager_user.check_password("manager12345"):
            manager_user.set_password("manager12345")
            manager_user.first_name = "Finance"
            manager_user.last_name = "Admin"
            manager_user.email = "manager@cashly.local"
            manager_user.save()
        assign_user_to_role(manager_user, ROLE_FINANCIAL_MANAGER)

        # Clear existing demo transactions and budgets to seed fresh illustrative data
        Transaction.objects.filter(user=demo_user).delete()
        Budget.objects.filter(user=demo_user).delete()
        SavingsGoal.objects.filter(user=demo_user).delete()

        now = timezone.now()
        today = now.date()

        # Seed Transactions for current month
        self.stdout.write("Creating transactions for demo user...")
        # Incomes
        Transaction.objects.create(
            user=demo_user,
            category=cats["Salary"],
            transaction_type="INCOME",
            amount=Decimal("500000.00"),
            date=today.replace(day=1),
            description="Monthly Base Salary Deposit"
        )
        Transaction.objects.create(
            user=demo_user,
            category=cats["Freelance & Side Hustle"],
            transaction_type="INCOME",
            amount=Decimal("120000.00"),
            date=today.replace(day=min(today.day, 5)),
            description="Client UI Design Contract"
        )

        # Expenses
        expenses_to_seed = [
            ("Rent & Housing", Decimal("160000.00"), 2, "Apartment Monthly Rent"),
            ("Utilities & Internet", Decimal("25000.00"), 4, "Fiber Internet & Electricity"),
            ("Food & Dining", Decimal("45000.00"), 6, "Bi-weekly Groceries Market"),
            ("Food & Dining", Decimal("18000.00"), 8, "Dinner with Colleagues"),
            ("Transport & Commute", Decimal("15000.00"), 9, "Fuel & City Bus Card Top-up"),
            ("Shopping & Groceries", Decimal("22000.00"), 10, "Household essentials & supplies"),
            ("Education & Books", Decimal("15000.00"), 11, "Python & System Architecture Book"),
            ("Entertainment & Leisure", Decimal("12000.00"), 12, "Cinema and Weekend Outing"),
        ]

        for cat_name, amt, day_offset, desc in expenses_to_seed:
            day_val = min(day_offset, today.day)
            t_date = today.replace(day=max(1, day_val))
            Transaction.objects.create(
                user=demo_user,
                category=cats[cat_name],
                transaction_type="EXPENSE",
                amount=amt,
                date=t_date,
                description=desc
            )

        # Seed Previous Month (for trend comparison)
        prev_month = 12 if today.month == 1 else today.month - 1
        prev_year = today.year - 1 if today.month == 1 else today.year
        Transaction.objects.create(
            user=demo_user,
            category=cats["Salary"],
            transaction_type="INCOME",
            amount=Decimal("500000.00"),
            date=today.replace(year=prev_year, month=prev_month, day=1),
            description="Previous Month Salary"
        )
        Transaction.objects.create(
            user=demo_user,
            category=cats["Food & Dining"],
            transaction_type="EXPENSE",
            amount=Decimal("85000.00"),
            date=today.replace(year=prev_year, month=prev_month, day=10),
            description="Previous Month Food"
        )
        Transaction.objects.create(
            user=demo_user,
            category=cats["Rent & Housing"],
            transaction_type="EXPENSE",
            amount=Decimal("160000.00"),
            date=today.replace(year=prev_year, month=prev_month, day=2),
            description="Previous Month Rent"
        )

        # Seed Budgets for current month
        self.stdout.write("Creating monthly budgets...")
        budgets_to_seed = [
            ("Food & Dining", Decimal("80000.00"), Decimal("80.0")),
            ("Rent & Housing", Decimal("160000.00"), Decimal("95.0")),
            ("Transport & Commute", Decimal("30000.00"), Decimal("75.0")),
            ("Utilities & Internet", Decimal("35000.00"), Decimal("80.0")),
            ("Entertainment & Leisure", Decimal("25000.00"), Decimal("70.0")),
            ("Shopping & Groceries", Decimal("40000.00"), Decimal("80.0")),
        ]

        for cat_name, b_limit, threshold in budgets_to_seed:
            Budget.objects.create(
                user=demo_user,
                category=cats[cat_name],
                amount=b_limit,
                period_month=today.month,
                period_year=today.year,
                alert_threshold=threshold
            )

        # Seed Savings Goals
        self.stdout.write("Creating savings goals...")
        laptop_goal = SavingsGoal.objects.create(
            user=demo_user,
            title="New Workstation Laptop",
            target_amount=Decimal("850000.00"),
            current_amount=Decimal("520000.00"),
            target_date=today + timedelta(days=90),
            notes="Saving for high-performance development laptop"
        )
        SavingsContribution.objects.create(
            goal=laptop_goal,
            amount=Decimal("150000.00"),
            date=today.replace(day=2),
            notes="Initial deposit from freelance project"
        )

        emergency_goal = SavingsGoal.objects.create(
            user=demo_user,
            title="6-Month Emergency Fund",
            target_amount=Decimal("1200000.00"),
            current_amount=Decimal("800000.00"),
            target_date=today + timedelta(days=180),
            notes="Safety net covering essential living expenses"
        )

        # Check and generate alerts
        check_and_generate_alerts(demo_user)

        self.stdout.write(self.style.SUCCESS("Successfully seeded Cashly demo data and roles!"))
