from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Employee, Company, CustomUser

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'id_number', 'tax_number',
            'salary', 'is_wage_employee', 'hourly_rate',
            'department', 'job_title', 'profile_picture'
        ]
        widgets = {
            'is_wage_employee': forms.CheckboxInput(),
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


