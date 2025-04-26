from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Employee, Company, CustomUser, Payslip, WorkedHours, LeaveRequest, LeaveType, LeaveBalance


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


class PayslipForm(forms.ModelForm):
    class Meta:
        model = Payslip
        fields = ['basic_salary', 'tax', 'uif', 'net_pay']  

class WorkedHoursForm(forms.ModelForm):
    class Meta:
        model = WorkedHours
        fields = ['normal_hours', 'overtime_hours', 'saturday_hours', 'sunday_public_hours']


class LeaveRequestForm(forms.ModelForm):
    """Form for creating leave requests with validation based on SA BCEA policies"""
    
    # Additional fields for specific leave types
    expected_birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    actual_birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    documentation_reference = forms.CharField(
        required=False,
        max_length=255,
        help_text="Reference number for supporting documentation"
    )
    
    class Meta:
        model = LeaveRequest
        fields = [
            'leave_type', 'start_date', 'end_date', 'reason',
            'expected_birth_date', 'actual_birth_date', 'documentation_reference'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get employee from kwargs to check available leave types
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Make some fields required only for specific leave types
        if self.employee:
            # Filter leave types based on eligibility (e.g., gender for maternity)
            available_types = LeaveType.choices
            
            # Example: Filter maternity leave by gender if your Employee model has gender
            if hasattr(self.employee, 'gender') and self.employee.gender != 'F':
                available_types = [lt for lt in LeaveType.choices if lt[0] != LeaveType.MATERNITY]
            
            self.fields['leave_type'].choices = available_types
    
    def clean(self):
        cleaned_data = super().clean()
        leave_type = cleaned_data.get('leave_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date cannot be before start date")
            
            # Calculate business days between dates (excluding weekends)
            days_count = self.calculate_business_days(start_date, end_date)
            cleaned_data['days_requested'] = days_count
            
            # Check if employee has enough leave balance
            if self.employee and leave_type not in [LeaveType.MATERNITY, LeaveType.PARENTAL]:
                try:
                    leave_balance = LeaveBalance.objects.get(
                        employee=self.employee,
                        leave_type=leave_type
                    )
                    if days_count > leave_balance.remaining_days:
                        raise forms.ValidationError(
                            f"You only have {leave_balance.remaining_days} days of "
                            f"{leave_balance.get_leave_type_display()} leave remaining"
                        )
                except LeaveBalance.DoesNotExist:
                    raise forms.ValidationError("Leave balance not found for this leave type")
        
        # Validate fields based on leave type
        if leave_type == LeaveType.MATERNITY:
            expected_birth_date = cleaned_data.get('expected_birth_date')
            if not expected_birth_date:
                self.add_error('expected_birth_date', "Required for maternity leave")
            elif start_date > expected_birth_date:
                self.add_error('start_date', "Maternity leave must start on or before expected birth date")
        
        elif leave_type == LeaveType.PARENTAL:
            expected_birth_date = cleaned_data.get('expected_birth_date')
            actual_birth_date = cleaned_data.get('actual_birth_date')
            if not expected_birth_date and not actual_birth_date:
                self.add_error('expected_birth_date', "Either expected or actual birth date is required")
            
            # Check if within 4 months
            reference_date = actual_birth_date if actual_birth_date else expected_birth_date
            if reference_date and start_date:
                days_difference = (start_date - reference_date).days
                if days_difference > 120:  # 4 months in days
                    self.add_error('start_date', 
                                  "Parental leave must be taken within 4 months of birth/adoption")
        
        elif leave_type == LeaveType.FAMILY:
            reason = cleaned_data.get('reason')
            if not reason:
                self.add_error('reason', "Reason is required for family responsibility leave")
        
        return cleaned_data
    
    def calculate_business_days(self, start_date, end_date):
        """Calculate business days between two dates, excluding weekends"""
        days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Weekday
                days += 1
            current_date += timezone.timedelta(days=1)
        
        return days