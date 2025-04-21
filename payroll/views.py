from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import EmployeeForm
from .models import Employee, Company
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import CompanyLoginForm
from .forms import CustomUserCreationForm


@login_required
def dashboard(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id) if company_id else None
    active_employees = Employee.objects.filter(status='active').count()
    return render(request, 'payroll/dashboard.html', {
        'company': company,
        'active_employees': active_employees
        })


def employee_list(request):
    employees = Employee.objects.filter(company=request.user.company, status='active')
    return render(request, 'employees/employee_list.html', {'employees': employees})


def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(instance=employee)
    company = employee.company
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'form': form,
        'company': company 
    })


def create_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save()  # Capture the saved instance
            return redirect('employee_detail', pk=employee.pk)  # Pass the PK here
    else:
        form = EmployeeForm()
    return render(request, 'employees/create_employee.html', {'form': form})


def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee updated successfully.")
        else:
            messages.error(request, "There was an error updating the employee.")
    return redirect('employee_detail', pk=employee.pk)


def custom_login_view(request):
    if request.method == 'POST':
        form = CompanyLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Save selected company in session
            request.session['company_id'] = form.cleaned_data['company'].id
            return redirect('dashboard')
    else:
        form = CompanyLoginForm(request)
    return render(request, 'payroll/login.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Automatically log the user in
            messages.success(request, "Registration successful.")
            return redirect('dashboard')  # Redirect to the dashboard after successful registration
        else:
            messages.error(request, "There was an error during registration.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'payroll/register.html', {'form': form})
