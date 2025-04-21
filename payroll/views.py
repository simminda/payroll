from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import EmployeeForm
from .models import Employee

def employee_list(request):
    employees = Employee.objects.filter(status='active')
    return render(request, 'employees/employee_list.html', {'employees': employees})


def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(instance=employee)
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'form': form
    })

def create_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('employee_success')  
    else:
        form = EmployeeForm()
    return render(request, 'employees/create_employee.html', {'form': form})

def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee updated successfully.")
        else:
            messages.error(request, "There was an error updating the employee.")
    return redirect('employee_detail', pk=employee.pk)
