from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'Create a secure password'
    }))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'Confirm your password'
    }))
    currency_code = forms.ChoiceField(
        choices=[('RWF', 'RWF - Rwandan Franc'), ('USD', 'USD - US Dollar'), ('EUR', 'EUR - Euro'), ('GBP', 'GBP - British Pound'), ('KES', 'KES - Kenyan Shilling')],
        initial='RWF',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. alex250'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'e.g. alex@example.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-input'}))

    class Meta:
        model = UserProfile
        fields = ['currency_code', 'currency_symbol', 'monthly_budget_target']
        widgets = {
            'currency_code': forms.Select(
                choices=[('RWF', 'RWF (Rwandan Franc)'), ('USD', 'USD ($)'), ('EUR', 'EUR (€)'), ('GBP', 'GBP (£)'), ('KES', 'KES (KSh)')],
                attrs={'class': 'form-select'}
            ),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. FRW, $, €'}),
            'monthly_budget_target': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }
