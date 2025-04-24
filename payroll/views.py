from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages
from .forms import EmployeeForm
from .models import Employee, Company, Payslip, PayrollRun, WorkedHours
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import CompanyLoginForm
from .forms import CustomUserCreationForm, PayslipForm, WorkedHoursForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum
import datetime
from datetime import date, timedelta
from payroll.utils import calculate_tax



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
    query = request.GET.get('q', '')

    # Step 1: Get active employees
    active_employees = Employee.objects.filter(status="active")

    # Apply search
    if query:
        active_employees = active_employees.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(id_number__icontains=query)
        )

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
    SDL_RATE = Decimal('0.01')
    CURRENT_TAX_YEAR = "2024/2025"

    for employee in active_employees:
        # Calculate all values first
        if employee.is_wage_employee:
            try:
                worked_hours = WorkedHours.objects.get(employee=employee, payroll_run=payroll_run)
                gross_income = worked_hours.calculate_gross_pay()
            except WorkedHours.DoesNotExist:
                gross_income = Decimal('0.00')
        else:
            gross_income = employee.salary or Decimal('0.00')
        
        # Calculate YTD gross income (excluding this month)
        start_of_tax_year = datetime.date(today.year, 3, 1)  # SA tax year: March to Feb
        ytd_income = Payslip.objects.filter(
            employee=employee,
            payroll_run__period_start__gte=start_of_tax_year,
            payroll_run__period_start__lt=period_start
        ).aggregate(total=Sum('basic_salary'))['total'] or Decimal('0.00')
        
        months_paid = Payslip.objects.filter(
            employee=employee,
            payroll_run__period_start__gte=start_of_tax_year,
            payroll_run__period_start__lt=period_start
        ).count() + 1  # Include this month
        
        # Avoid division by zero
        if months_paid == 0:
            annualized_income = gross_income * 12
        else:
            annualized_income = (ytd_income + gross_income) / months_paid * 12

        # Determine the rebate based on age
        age = employee.age or 0
        rebate = Decimal('17235.00')  # Base rebate
        if age >= 65:
            rebate += Decimal('9444.00')
        if age >= 75:
            rebate += Decimal('3145.00')

        # Calculate tax based on annualized income minus applicable rebate
        annual_tax = calculate_tax(annualized_income, CURRENT_TAX_YEAR, rebate)
        tax = annual_tax / 12
        
        # UIF
        uif_income = min(gross_income, UIF_CEILING)
        uif = uif_income * UIF_RATE
        
        # SDL
        sdl = gross_income * SDL_RATE
        
        # Net pay
        net_pay = gross_income - tax - uif - sdl
        
        # Now use get_or_create with all the values in defaults
        payslip, created = Payslip.objects.get_or_create(
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
        
        # If the payslip already existed, update its values
        if not created:
            payslip.basic_salary = gross_income
            payslip.tax = tax
            payslip.uif = uif
            payslip.sdl = sdl
            payslip.net_pay = net_pay
            payslip.save()

        # Get worked hours for the employee and payroll run
        worked_hours = WorkedHours.objects.filter(
            employee=employee, payroll_run=payroll_run
        ).first()
        
        # Store worked hours in a dictionary tied to payslip ID for easy access in template
        payslip.worked_hours = worked_hours

    # Step 5: Retrieve all payslips for the current payroll run
    payslips = Payslip.objects.filter(payroll_run=payroll_run, employee__in=active_employees)

    # Attach WorkedHours to each payslip
    for payslip in payslips:
        payslip.worked_hours = WorkedHours.objects.filter(
            employee=payslip.employee,
            payroll_run=payslip.payroll_run
        ).first()

    # Step 6: Calculate totals
    totals = {
        'basic_salary_total': sum(p.basic_salary or 0 for p in payslips if p.basic_salary is not None),
        'gross_income': sum(p.gross_income or 0 for p in payslips),
        'tax': sum(p.tax for p in payslips),
        'uif': sum(p.uif for p in payslips),
        'net_pay': sum(p.net_pay for p in payslips),
        # WorkedHours breakdown 
        'normal_hours_total': sum(p.worked_hours.normal_earnings or 0 for p in payslips if p.worked_hours),
        'overtime_hours_total': sum(p.worked_hours.overtime_earnings or 0 for p in payslips if p.worked_hours),
        'saturday_hours_total': sum(p.worked_hours.saturday_earnings or 0 for p in payslips if p.worked_hours),
        'sunday_hours_total': sum(p.worked_hours.sunday_earnings or 0 for p in payslips if p.worked_hours),
    }

    paginator = Paginator(payslips, 10)
    page_number = request.GET.get("page")
    payslips = paginator.get_page(page_number)

    return render(request, 'payslips/payslips_summary.html', {
        'payslips': payslips,
        'totals': totals,
        'payroll_run': payroll_run,
        'query': query,
        'worked_hours': worked_hours
    })


def payslip_detail(request, pk):
    payslip = get_object_or_404(Payslip, pk=pk)
    return render(request, 'payslips/payslip_detail.html', {'payslip': payslip})


def update_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)
    
    # Try to get WorkedHours if it exists
    worked_hours = WorkedHours.objects.filter(
        employee=payslip.employee, payroll_run=payslip.payroll_run
    ).first()

    if request.method == 'POST':
        payslip_form = PayslipForm(request.POST, instance=payslip)
        hours_form = WorkedHoursForm(request.POST, instance=worked_hours)

        if payslip_form.is_valid() and hours_form.is_valid():
            payslip_form.save()
            hours_form.save()
            return redirect('payslips_summary')
        
    else:
        payslip_form = PayslipForm(instance=payslip)
        hours_form = WorkedHoursForm(instance=worked_hours)

    return redirect('payslips_summary')