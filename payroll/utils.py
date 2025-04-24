from decimal import Decimal, ROUND_HALF_UP
from .models import ContributionType, TaxBracket 


def calculate_contribution(contribution_type, gross_income):
    """
    Calculates employee and employer contributions based on rules defined
    in the ContributionType model. Applies caps where relevant.
    """

    # Ensure Decimal math
    gross_income = Decimal(gross_income)

    if contribution_type.formula == 'percentage':
        employee_amount = gross_income * contribution_type.employee_rate
        employer_amount = gross_income * contribution_type.employer_rate
    elif contribution_type.formula == 'fixed':
        employee_amount = contribution_type.max_employee_amount or Decimal('0.00')
        employer_amount = contribution_type.max_employer_amount or Decimal('0.00')
    elif contribution_type.formula == 'custom':
        # TODO: hook up custom logic later if needed
        employee_amount = Decimal('0.00')
        employer_amount = Decimal('0.00')
    else:
        employee_amount = Decimal('0.00')
        employer_amount = Decimal('0.00')

    # Apply caps
    if contribution_type.max_employee_amount:
        employee_amount = min(employee_amount, contribution_type.max_employee_amount)
    if contribution_type.max_employer_amount:
        employer_amount = min(employer_amount, contribution_type.max_employer_amount)

    # Round amounts properly
    employee_amount = employee_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    employer_amount = employer_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return employee_amount, employer_amount


def calculate_tax(income, tax_year, rebate=Decimal('0.00')):
    brackets = TaxBracket.objects.filter(tax_year=tax_year).order_by('lower_limit')
    for bracket in brackets:
        if bracket.upper_limit is None or income <= bracket.upper_limit:
            tax_before_rebate = bracket.base_tax + ((income - bracket.lower_limit) * (bracket.marginal_rate / 100))
            tax_after_rebate = max(tax_before_rebate - rebate, Decimal('0.00'))
            return tax_after_rebate
    return Decimal('0.00')
