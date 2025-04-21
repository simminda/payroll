from django.conf import settings
from django.shortcuts import render
from django.urls import path
from django.conf.urls.static import static
from .views import create_employee, employee_list, employee_detail, edit_employee


urlpatterns = [
    path('', employee_list, name='employee_list'),
    path('create/', create_employee, name='create_employee'),
    path('<int:pk>/', employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', edit_employee, name='edit_employee'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


