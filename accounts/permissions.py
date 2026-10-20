from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from functools import wraps


# Role Definitions
ROLE_STANDARD_USER = "Standard User"
ROLE_FINANCIAL_MANAGER = "Financial Manager"
ROLE_AUDITOR = "Auditor"
ROLE_VIEWER = "Viewer"

ALL_ROLES = [
    ROLE_STANDARD_USER,
    ROLE_FINANCIAL_MANAGER,
    ROLE_AUDITOR,
    ROLE_VIEWER,
]


def setup_roles_and_permissions():
    """
    Creates or updates the standard User Groups and assigns
    the appropriate model and custom permissions.
    """
    from finances.models import Category, Transaction, Budget, SavingsGoal

    # Content Types
    cat_ct = ContentType.objects.get_for_model(Category)
    tx_ct = ContentType.objects.get_for_model(Transaction)
    budget_ct = ContentType.objects.get_for_model(Budget)
    goal_ct = ContentType.objects.get_for_model(SavingsGoal)

    # 1. Standard User
    standard_group, _ = Group.objects.get_or_create(name=ROLE_STANDARD_USER)
    standard_codenames = [
        # Standard CRUD for personal transactions
        'add_transaction', 'change_transaction', 'delete_transaction', 'view_transaction',
        'add_budget', 'change_budget', 'delete_budget', 'view_budget',
        'add_savingsgoal', 'change_savingsgoal', 'delete_savingsgoal', 'view_savingsgoal',
        'add_category', 'change_category', 'view_category',
        'can_export_transactions',
    ]
    standard_perms = Permission.objects.filter(codename__in=standard_codenames)
    standard_group.permissions.set(standard_perms)

    # 2. Financial Manager
    manager_group, _ = Group.objects.get_or_create(name=ROLE_FINANCIAL_MANAGER)
    manager_codenames = standard_codenames + [
        'can_manage_shared_categories',
        'can_override_budget_limit',
        'can_view_department_budgets',
        'can_audit_all_transactions',
        'delete_category',
    ]
    manager_perms = Permission.objects.filter(codename__in=manager_codenames)
    manager_group.permissions.set(manager_perms)

    # 3. Auditor
    auditor_group, _ = Group.objects.get_or_create(name=ROLE_AUDITOR)
    auditor_codenames = [
        'view_transaction',
        'view_budget',
        'view_savingsgoal',
        'view_category',
        'can_export_transactions',
        'can_audit_all_transactions',
        'can_view_department_budgets',
    ]
    auditor_perms = Permission.objects.filter(codename__in=auditor_codenames)
    auditor_group.permissions.set(auditor_perms)

    # 4. Viewer
    viewer_group, _ = Group.objects.get_or_create(name=ROLE_VIEWER)
    viewer_codenames = [
        'view_transaction',
        'view_budget',
        'view_savingsgoal',
        'view_category',
    ]
    viewer_perms = Permission.objects.filter(codename__in=viewer_codenames)
    viewer_group.permissions.set(viewer_perms)

    return {
        ROLE_STANDARD_USER: standard_group,
        ROLE_FINANCIAL_MANAGER: manager_group,
        ROLE_AUDITOR: auditor_group,
        ROLE_VIEWER: viewer_group,
    }


def assign_user_to_role(user, role_name):
    """Assigns user to a specified role and removes conflicting roles."""
    group, _ = Group.objects.get_or_create(name=role_name)
    # Remove from other pre-defined role groups
    for r in ALL_ROLES:
        try:
            g = Group.objects.get(name=r)
            user.groups.remove(g)
        except Exception:
            pass
    user.groups.add(group)


def get_user_role(user):
    """Returns the primary role of a user for UI badge display."""
    if user.is_superuser:
        return "Administrator"
    group = user.groups.filter(name__in=ALL_ROLES).first()
    return group.name if group else ROLE_STANDARD_USER


def require_permission_or_owner(perm_codename=None):
    """
    Decorator to verify that user is logged in, has the permission,
    or has proper group clearance.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('accounts:login')
            if perm_codename and not (request.user.has_perm(perm_codename) or request.user.is_superuser):
                raise PermissionDenied("You do not have the required permissions to perform this action.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
