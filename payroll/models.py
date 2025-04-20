from django.db import models

class Employee(models.Model):
    """
    Represents an employee in the payroll system.
    Stores both salaried and wage-based employee details.
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=13)
    tax_number = models.CharField(max_length=20, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_wage_employee = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='employee_pictures/', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


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
