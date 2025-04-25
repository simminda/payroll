from django.db import models
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from datetime import date
from django.db.models import Sum


import datetime


class Company(models.Model):
    """
    Represents a company using the payroll system.
    """
    code = models.CharField(max_length=7, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.code})"
    

class CustomUser(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    

class Employee(models.Model):
    """
    Represents an employee in the payroll system.
    Stores both salaried and wage-based employee details.
    """
    EMPLOYMENT_STATUSES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
        ('deceased', 'Deceased'),
        ('retired', 'Retired'),
        ('maternity_leave', 'Maternity Leave'),
        ('probation', 'Probation'),
        ('resigned', 'Resigned'),
    ]

    DEPARTMENT_CHOICES = [
        ('Operations', 'Operations'),
        ('Debtors', 'Debtors'),
        ('Creditors', 'Creditors'),
        ('Finance', 'Finance'),
        ('Marketing', 'Marketing'),
        ('Maintenance', 'Maintenance'),
        ('Admin', 'Admin'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_joined = models.DateField(default=date(2025, 4, 1))
    id_number = models.CharField(max_length=13)
    tax_number = models.CharField(max_length=20, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_wage_employee = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='employee_pictures/', blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees", default=1)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUSES, default='active')
    status_changed_at = models.DateTimeField(null=True, blank=True)

    @property
    def birthdate(self):
        """
        Extracts birthdate from the South African ID number (YYMMDD format).
        Assumes all IDs are valid and for individuals born in the 1900s or 2000s.
        """
        if self.id_number and len(self.id_number) == 13:
            yy = int(self.id_number[:2])
            mm = int(self.id_number[2:4])
            dd = int(self.id_number[4:6])

            # Determine the century
            current_year = date.today().year % 100
            century = 1900 if yy > current_year else 2000
            try:
                return date(century + yy, mm, dd)
            except ValueError:
                return None
        return None

    @property
    def age(self):
        if self.birthdate:
            today = date.today()
            return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
        return None

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def calculate_hourly_rate(self, config=None):
        if config:
            monthly_hours = config.monthly_hours()
        else:
            weekly_hours = getattr(settings, 'DEFAULT_WEEKLY_HOURS', 45)
            monthly_hours = Decimal(str(weekly_hours)) * Decimal('4.33')  # Apprx per week
        return self.salary / monthly_hours if self.salary else None

    def save(self, *args, **kwargs):
        # Handle status change timestamp
        if self.pk:
            old = Employee.objects.get(pk=self.pk)
            if old.status != self.status:
                self.status_changed_at = timezone.now()
        else:
            self.status_changed_at = timezone.now()

        # Handle hourly rate logic
        if self.is_wage_employee:
            if self.hourly_rate is None:
                self.hourly_rate = 0
        elif self.salary:
            config = WorkingHoursConfig.objects.filter(active=True).first()
            self.hourly_rate = self.calculate_hourly_rate(config)

        super().save(*args, **kwargs)


class PayrollRun(models.Model):
    """
    Represents a single payroll period (e.g. monthly run).
    Only one can be active at a time. Closed runs cannot be modified.
    """
    period_start = models.DateField()
    period_end = models.DateField()
    is_active = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payroll Run: {self.period_start} to {self.period_end}"

    class Meta:
        ordering = ['-period_start']


class WorkedHours(models.Model):
    """
    Captures hours worked by wage-based employees for a specific payroll run.
    Includes normal, overtime, Saturday, and Sunday/public holiday hours.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)

    normal_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    saturday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sunday_public_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def normal_earnings(self):
        return self.normal_hours * self.employee.hourly_rate

    @property
    def overtime_earnings(self):
        return self.overtime_hours * self.employee.hourly_rate * Decimal("1.5")

    @property
    def saturday_earnings(self):
        return self.saturday_hours * self.employee.hourly_rate * Decimal("1.5")

    @property
    def sunday_earnings(self):
        return self.sunday_public_hours * self.employee.hourly_rate * Decimal("2")

    def calculate_gross_pay(self):
        normal = self.normal_hours or 0
        ot_1_5 = self.overtime_hours or 0
        sat_1_5 = self.saturday_hours or 0
        sun_2_0 = self.sunday_public_hours or 0

        hourly = self.employee.hourly_rate or Decimal("0.00")

        gross = (
            Decimal(normal) * hourly +
            Decimal(ot_1_5) * hourly * Decimal("1.5") +
            Decimal(sat_1_5) * hourly * Decimal("1.5") +
            Decimal(sun_2_0) * hourly * Decimal("2.0")
        )
        return gross


class Payslip(models.Model):
    """
    Stores calculated payslip details for an employee in a given payroll run.
    Includes gross income, deductions, and net pay.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    gross_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    uif = models.DecimalField(max_digits=10, decimal_places=2)
    sdl = models.DecimalField(max_digits=10, decimal_places=2)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    worked_hours = models.OneToOneField(
        'WorkedHours',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = ('employee', 'payroll_run')

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} – {self.payroll_run.period_start.strftime('%b %Y')}"
    
    def get_income_total(self):
        wh = self.worked_hours
        return (
            (self.basic_salary or 0) +
            (wh.normal_earnings if wh else 0) +
            (wh.overtime_earnings if wh else 0) +
            (wh.saturday_earnings if wh else 0) +
            (wh.sunday_earnings if wh else 0)
        )

    def get_deductions_total(self):
        return (self.tax or 0) + (self.uif or 0)
    
    def get_wages_total(self):
        wh = self.worked_hours
        return (
            (wh.normal_earnings if wh else 0) +
            (wh.overtime_earnings if wh else 0) +
            (wh.saturday_earnings if wh else 0) +
            (wh.sunday_earnings if wh else 0)
        )
    
    @property
    def ytd_basic_salary(self):
        if not self.employee.is_wage_employee:
            start = datetime.date(self.payroll_run.period_start.year, 3, 1)
            return Payslip.objects.filter(
                employee=self.employee,
                payroll_run__period_start__gte=start,
                payroll_run__period_start__lte=self.payroll_run.period_start
            ).aggregate(total=Sum('basic_salary'))['total'] or Decimal('0.00')
        return Decimal('0.00')
    
    @property
    def ytd_wages(self):
        if self.employee.is_wage_employee:
            start = datetime.date(self.payroll_run.period_start.year, 3, 1)
            payslips = Payslip.objects.filter(
                employee=self.employee,
                payroll_run__period_start__gte=start,
                payroll_run__period_start__lte=self.payroll_run.period_start
            ).select_related('worked_hours')

            total = Decimal('0.00')
            for slip in payslips:
                wh = slip.worked_hours
                if wh:
                    total += (
                        wh.normal_earnings +
                        wh.overtime_earnings +
                        wh.saturday_earnings +
                        wh.sunday_earnings
                    )
            return total
        return Decimal('0.00')
    
    @property
    def ytd_net_pay(self):
        start_of_tax_year = datetime.date(self.payroll_run.period_start.year, 3, 1)
        return Payslip.objects.filter(
            employee=self.employee,
            payroll_run__period_start__gte=start_of_tax_year,
            payroll_run__period_start__lte=self.payroll_run.period_start
        ).aggregate(total=Sum('net_pay'))['total'] or Decimal('0.00')
    
    @property
    def ytd_gross_income(self):
        start = datetime.date(self.payroll_run.period_start.year, 3, 1)
        return Payslip.objects.filter(
            employee=self.employee,
            payroll_run__period_start__gte=start,
            payroll_run__period_start__lte=self.payroll_run.period_start
        ).aggregate(total=Sum('gross_income'))['total'] or Decimal('0.00')

    @property
    def ytd_total_deductions(self):
        return (self.tax or Decimal('0.00')) + (self.uif or Decimal('0.00'))

    @property
    def ytd_tax(self):
        start = datetime.date(self.payroll_run.period_start.year, 3, 1)
        return Payslip.objects.filter(
            employee=self.employee,
            payroll_run__period_start__gte=start,
            payroll_run__period_start__lte=self.payroll_run.period_start
        ).aggregate(total=Sum('tax'))['total'] or Decimal('0.00')
    
    @property
    def ytd_uif(self):
        start = datetime.date(self.payroll_run.period_start.year, 3, 1)
        return Payslip.objects.filter(
            employee=self.employee,
            payroll_run__period_start__gte=start,
            payroll_run__period_start__lte=self.payroll_run.period_start
        ).aggregate(total=Sum('uif'))['total'] or Decimal('0.00')
    
    @property
    def ytd_sdl(self):
        start = datetime.date(self.payroll_run.period_start.year, 3, 1)
        return Payslip.objects.filter(
            employee=self.employee,
            payroll_run__period_start__gte=start,
            payroll_run__period_start__lte=self.payroll_run.period_start
        ).aggregate(total=Sum('sdl'))['total'] or Decimal('0.00')
    
    @property
    def total_employer_contribution(self):
        return (self.sdl or Decimal('0.00')) + (self.uif or Decimal('0.00'))
    
    @property
    def ytd_total_employer_contribution(self):
        start = datetime.date(self.payroll_run.period_start.year, 3, 1)
        totals = Payslip.objects.filter(
            employee=self.employee,
            payroll_run__period_start__gte=start,
            payroll_run__period_start__lte=self.payroll_run.period_start
        ).aggregate(
            total_sdl=Sum('sdl'),
            total_uif=Sum('uif')
        )
        return (totals['total_sdl'] or Decimal('0.00')) + (totals['total_uif'] or Decimal('0.00'))

    def save(self, *args, **kwargs):
        if self.employee.is_wage_employee:
            try:
                hours = WorkedHours.objects.get(employee=self.employee, payroll_run=self.payroll_run)
                self.worked_hours = hours
                self.gross_income = hours.calculate_gross_pay()
            except WorkedHours.DoesNotExist:
                self.worked_hours = None
                self.gross_income = 0
            self.basic_salary = None  # Optional but good for clarity
        else:
            self.worked_hours = None  # No worked hours for salaried employees
            self.gross_income = self.basic_salary or 0

        super().save(*args, **kwargs)



class AllowanceType(models.Model):
    """
    Defines a type of allowance (e.g. travel, meal, housing).
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Allowance(models.Model):
    """
    Records a specific allowance paid to an employee in a given payroll run.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.allowance_type} - {self.amount} ({self.employee})"

    class Meta:
        unique_together = ('employee', 'payroll_run', 'allowance_type')


class DeductionType(models.Model):
    """
    Defines a type of deduction (e.g. loan, garnishee, union fees).
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Deduction(models.Model):
    """
    Records a specific deduction applied to an employee's payslip for a payroll run.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    deduction_type = models.ForeignKey(DeductionType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.deduction_type} - {self.amount} ({self.employee})"

    class Meta:
        unique_together = ('employee', 'payroll_run', 'deduction_type')


class ContributionType(models.Model):
    """
    Defines employer/employee contributions (e.g. UIF, SDL, Pension).
    Supports percentage, fixed, or custom formulas with caps.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    employee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    employer_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    max_employee_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_employer_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    formula = models.CharField(
        max_length=50,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount'), ('custom', 'Custom')],
        default='percentage'
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CompanyContribution(models.Model):
    """
    Stores actual contribution amounts per employee for each payroll run
    based on the rules defined in ContributionType.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    contribution_type = models.ForeignKey(ContributionType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.contribution_type} - {self.amount} ({self.employee})"

    class Meta:
        unique_together = ('employee', 'payroll_run', 'contribution_type')


class WorkingHoursConfig(models.Model):
    weekly_hours = models.DecimalField(max_digits=4, decimal_places=2, default=45.0)
    use_for_salaried_employees = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    def monthly_hours(self):
        return self.weekly_hours * Decimal("4.33")  # approx weeks/month

    def __str__(self):
        return f"{self.weekly_hours} hours/week (active={self.active})"

    class Meta:
        verbose_name = "Working Hours Configuration"
        verbose_name_plural = "Working Hours Configurations"


class TaxBracket(models.Model):
    tax_year = models.CharField(max_length=9)  # e.g., "2024/2025"
    lower_limit = models.DecimalField(max_digits=12, decimal_places=2)
    upper_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    base_tax = models.DecimalField(max_digits=12, decimal_places=2)
    marginal_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Enter as a percentage, e.g., 18 for 18%")

    class Meta:
        ordering = ['tax_year', 'lower_limit']

    def __str__(self):
        return f"{self.tax_year}: {self.lower_limit} - {self.upper_limit or '∞'}"