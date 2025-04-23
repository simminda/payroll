from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages
from .forms import EmployeeForm
from .models import Employee, Company, Payslip, PayrollRun
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import CompanyLoginForm
from .forms import CustomUserCreationForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from datetime import date, timedelta


VALID_STATUSES = [
    'active', 'suspended', 'terminated', 'on_leave',
    'deceased', 'retired', 'maternity_leave', 'probation', 'resigned'
]


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
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    # Base queryset scoped to the user's company
    employees = Employee.objects.filter(company=request.user.company)

    # Apply search
    if query:
        employees = employees.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(id_number__icontains=query)
        )

    if status_filter in VALID_STATUSES:
        employees = employees.filter(status=status_filter) 

    paginator = Paginator(employees, 10)
    page_number = request.GET.get("page")
    employees = paginator.get_page(page_number)

    return render(request, 'employees/employee_list.html', {
        'employees': employees
    })


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


def get_month_bounds(dt):
    start = dt.replace(day=1)
    if dt.month == 12:
        end = dt.replace(day=31)
    else:
        next_month = dt.replace(day=28) + timedelta(days=4)
        end = next_month.replace(day=1) - timedelta(days=1)
    return start, end

def payslips_summary(request):
    # Step 1: Get active employees
    active_employees = Employee.objects.filter(status="active")

    # Step 2: Define payroll period (start of current month to end of current month)
    today = timezone.now().date()
    period_start, period_end = get_month_bounds(today)

    # Step 3: Get or create the PayrollRun for this month
    payroll_run, created = PayrollRun.objects.get_or_create(
        period_start=period_start,
        period_end=period_end
    )

    # Step 4: Create missing Payslip objects for each active employee
    UIF_CEILING = Decimal('17712.00')
    UIF_RATE = Decimal('0.01')

    for employee in active_employees:
        gross_income = employee.salary if not employee.is_wage_employee and employee.salary else Decimal('0.00')
        tax = Decimal('0.00')
        # Apply UIF ceiling
        uif_income = min(gross_income, UIF_CEILING)
        uif = uif_income * UIF_RATE
        sdl = gross_income * Decimal('0.01')
        net_pay = gross_income - tax - uif - sdl

        Payslip.objects.get_or_create(
            employee=employee,
            payroll_run=payroll_run,
            defaults={
                'gross_income': gross_income,
                'tax': tax,
                'uif': uif,
                'sdl': sdl,
                'net_pay': net_pay,
            }
        )

    # Step 5: Retrieve all payslips for the current payroll run
    payslips = Payslip.objects.filter(payroll_run=payroll_run)

    # Step 6: Calculate totals
    totals = {
        'gross_income': sum(p.gross_income for p in payslips),
        'tax': sum(p.tax for p in payslips),
        'uif': sum(p.uif for p in payslips),
        'sdl': sum(p.sdl for p in payslips),
        'net_pay': sum(p.net_pay for p in payslips),
    }

    return render(request, 'payslips/payslips_summary.html', {
        'payslips': payslips,
        'totals': totals,
        'payroll_run': payroll_run,
    })


def payslip_detail(request, pk):
    payslip = get_object_or_404(Payslip, pk=pk)
    return render(request, 'payslips/payslip_detail.html', {'payslip': payslip})