from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Employee, Company, CustomUser


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        exclude = ['status_changed_at'] 
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_wage_employee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CompanyLoginForm(AuthenticationForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes to username/password fields
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'

    def confirm_login_allowed(self, user):
        pass  # Skip extra checks like company matching


class CustomUserCreationForm(UserCreationForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'company')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes to all other fields
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'


