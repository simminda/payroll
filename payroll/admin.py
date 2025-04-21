from django.contrib import admin
from .models import Employee, PayrollRun, Payslip, WorkingHoursConfig

admin.site.register(Employee)
admin.site.register(PayrollRun)
admin.site.register(Payslip)

@admin.register(WorkingHoursConfig)
class WorkingHoursConfigAdmin(admin.ModelAdmin):
    list_display = ('weekly_hours', 'use_for_salaried_employees', 'active')
    list_filter = ('active',)