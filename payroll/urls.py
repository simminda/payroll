from django.conf import settings
from django.shortcuts import render
from django.urls import path
from django.conf.urls.static import static
from .views import dashboard, create_employee, employee_list, employee_detail, edit_employee, custom_login_view, register, payslip_detail, payslips_summary, update_payslip, leave_summary
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('employees', employee_list, name='employee_list'),
    path('create/', create_employee, name='create_employee'),
    path('<int:pk>/', employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', edit_employee, name='edit_employee'),
    path('login/', custom_login_view, name='login'),
    path('register/', register, name='register'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path("payslips/summary/", payslips_summary, name="payslips_summary"),
    path('payslip/<int:pk>/', payslip_detail, name='payslip_detail'),
    path('payslip/update/<int:payslip_id>/', update_payslip, name='update_payslip'),
    path("leave/summary/", leave_summary, name="leave_summary"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


