from .models import Company

def current_company(request):
    company_id = request.session.get('company_id')
    company = None
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            pass
    return {'company': company}
