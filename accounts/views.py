from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm
from .models import UserProfile
from .permissions import (
    setup_roles_and_permissions,
    assign_user_to_role,
    get_user_role,
    ROLE_STANDARD_USER,
    ROLE_FINANCIAL_MANAGER,
    ROLE_AUDITOR,
    ROLE_VIEWER,
    ALL_ROLES
)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('finances:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Ensure roles exist and assign default Standard User role
            setup_roles_and_permissions()
            assign_user_to_role(user, ROLE_STANDARD_USER)

            # Update profile currency
            currency_code = form.cleaned_data.get('currency_code', 'RWF')
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.currency_code = currency_code
            profile.currency_symbol = 'FRW' if currency_code == 'RWF' else '$'
            profile.save()

            messages.success(request, f"Welcome to Cashly, {user.username}! Your account has been created.")
            login(request, user)
            return redirect('finances:dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('finances:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'finances:dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('accounts:login')


def demo_login_view(request, role='standard'):
    """
    Convenient one-click login for evaluating Cashly features and permissions.
    """
    setup_roles_and_permissions()
    username = "manager" if role == 'manager' else "demo"
    password = "manager12345" if role == 'manager' else "demo12345"

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Fallback to create or retrieve
        from django.core.management import call_command
        try:
            call_command('seed_cashly')
            user = authenticate(request, username=username, password=password)
        except Exception:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.save()
            assign_user_to_role(user, ROLE_FINANCIAL_MANAGER if role == 'manager' else ROLE_STANDARD_USER)

    if user:
        login(request, user)
        role_label = get_user_role(user)
        messages.success(request, f"Logged in as demo user '{user.username}' with role: {role_label}")
        return redirect('finances:dashboard')

    messages.error(request, "Could not initialize demo login. Please register or try again.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()
            # Update user fields
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()

            # Handle role switch if requested
            new_role = request.POST.get('role_assignment')
            if new_role in ALL_ROLES:
                assign_user_to_role(request.user, new_role)

            messages.success(request, "Your profile and preferences have been updated.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(
            instance=profile,
            initial={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
        )

    current_role = get_user_role(request.user)
    user_permissions = request.user.get_all_permissions()

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
        'current_role': current_role,
        'all_roles': ALL_ROLES,
        'user_permissions': user_permissions,
    })
