# Generated by Django 5.2 on 2025-04-21 20:04

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0002_alter_employee_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='date_joined',
            field=models.DateField(default=datetime.date(2025, 4, 1)),
        ),
    ]
