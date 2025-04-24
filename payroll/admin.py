from django.contrib import admin
from .models import CustomUser, Employee, PayrollRun, Payslip, WorkingHoursConfig, Company, TaxBracket, WorkedHours

admin.site.register(CustomUser)
admin.site.register(Company)
admin.site.register(Employee)
admin.site.register(PayrollRun)
admin.site.register(Payslip)
admin.site.register(TaxBracket)
admin.site.register(WorkedHours)

@admin.register(WorkingHoursConfig)
class WorkingHoursConfigAdmin(admin.ModelAdmin):
    list_display = ('weekly_hours', 'use_for_salaried_employees', 'active')
    list_filter = ('active',)


class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "company", "department", "job_title", "status", 'date_joined')
    list_filter = ("company", "status", "department")
    search_fields = ("first_name", "last_name", "id_number", "tax_number", "company__name")
