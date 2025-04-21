from .models import Company, Employee

def current_company(request):
    company_id = request.session.get('company_id')
    company = None
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            pass
    return {'company': company}


def active_employees(request):
    # Query the count of active employees
    active_count = Employee.objects.filter(status='active').count()  
    return {
        'active_employees': active_count
    }