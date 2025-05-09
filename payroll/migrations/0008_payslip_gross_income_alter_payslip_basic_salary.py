# Generated by Django 5.2 on 2025-04-24 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0007_rename_gross_income_payslip_basic_salary'),
    ]

    operations = [
        migrations.AddField(
            model_name='payslip',
            name='gross_income',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='payslip',
            name='basic_salary',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
