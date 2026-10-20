from django import forms
from django.utils import timezone
from .models import Transaction, Budget, SavingsGoal, SavingsContribution, Category


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'category', 'date', 'description', 'notes']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Grocery store run or Monthly salary'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'placeholder': 'Optional details, receipt notes...', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Show shared categories and user's custom categories
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            ).order_by('category_type', 'name')
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'period_month', 'period_year', 'alert_threshold']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Monthly limit', 'step': '0.01'}),
            'period_month': forms.Select(
                choices=[(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
                attrs={'class': 'form-select'}
            ),
            'period_year': forms.NumberInput(attrs={'class': 'form-input'}),
            'alert_threshold': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '80.00', 'step': 'any', 'min': '0', 'max': '100'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        now = timezone.now()
        if not self.initial.get('period_month'):
            self.initial['period_month'] = now.month
        if not self.initial.get('period_year'):
            self.initial['period_year'] = now.year
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True),
                category_type='EXPENSE'
            ).order_by('name')


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ['title', 'target_amount', 'current_amount', 'target_date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. New Laptop, Emergency Fund'}),
            'target_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Target amount', 'step': '0.01'}),
            'current_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Initial saved amount', 'step': '0.01'}),
            'target_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'placeholder': 'Why are you saving for this?', 'rows': 2}),
        }


class SavingsContributionForm(forms.ModelForm):
    class Meta:
        model = SavingsContribution
        fields = ['amount', 'date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Contribution amount', 'step': '0.01', 'min': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Monthly transfer, bonus deposit'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category Name'}),
            'category_type': forms.Select(attrs={'class': 'form-select'}),
            'icon': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Icon name (e.g. tag, utensils, car)'}),
            'color': forms.TextInput(attrs={'class': 'form-input', 'type': 'color'}),
        }
