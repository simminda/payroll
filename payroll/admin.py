from django.contrib import admin
from .models import Employee, PayPeriod, Payslip

admin.site.register(Employee)
admin.site.register(PayPeriod)
admin.site.register(Payslip)
