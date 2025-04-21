from django import forms
from .models import Employee

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
