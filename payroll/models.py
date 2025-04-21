from django.db import models
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser



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
        ('terminated', 'Terminated'),
        ('suspended', 'Suspended'),
        ('on_leave', 'On Leave'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=13)
    tax_number = models.CharField(max_length=20, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_wage_employee = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='employee_pictures/', blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees", default=1)
    department = models.CharField(max_length=100, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUSES, default='active')
    status_changed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def calculate_hourly_rate(self, config=None):
        if config:
            monthly_hours = config.monthly_hours()
        else:
            weekly_hours = getattr(settings, 'DEFAULT_WEEKLY_HOURS', 45)
            monthly_hours = weekly_hours * 4.33  # Approximate weeks/month
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

    def calculate_gross_pay(self):
        """
        Calculates gross pay based on hours worked and applicable hourly rates.
        """
        if not self.employee.is_wage_employee:
            return self.employee.salary or 0

        rate = self.employee.hourly_rate or 0
        return (
            self.normal_hours * rate +
            self.overtime_hours * rate * 1.5 +
            self.saturday_hours * rate * 1.5 +
            self.sunday_public_hours * rate * 2
        )


class Payslip(models.Model):
    """
    Stores calculated payslip details for an employee in a given payroll run.
    Includes gross income, deductions, and net pay.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    gross_income = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    uif = models.DecimalField(max_digits=10, decimal_places=2)
    sdl = models.DecimalField(max_digits=10, decimal_places=2)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'payroll_run')


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
