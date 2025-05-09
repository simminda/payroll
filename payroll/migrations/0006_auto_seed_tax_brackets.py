# Generated by Django 5.2 on 2025-04-23 21:40

from django.db import migrations, models
from decimal import Decimal

def seed_tax_brackets(apps, schema_editor):
    TaxBracket = apps.get_model('payroll', 'TaxBracket')

    brackets = [
        # 2024/2025
        ("2024/2025", Decimal('0.00'), Decimal('237100.00'), Decimal('0.00'), Decimal('18')),
        ("2024/2025", Decimal('237100.01'), Decimal('370500.00'), Decimal('42678.00'), Decimal('26')),
        ("2024/2025", Decimal('370500.01'), Decimal('512800.00'), Decimal('77362.00'), Decimal('31')),
        ("2024/2025", Decimal('512800.01'), Decimal('673000.00'), Decimal('121475.00'), Decimal('36')),
        ("2024/2025", Decimal('673000.01'), Decimal('857900.00'), Decimal('179147.00'), Decimal('39')),
        ("2024/2025", Decimal('857900.01'), Decimal('1817000.00'), Decimal('251258.00'), Decimal('41')),
        ("2024/2025", Decimal('1817000.01'), None, Decimal('644489.00'), Decimal('45')),

        # 2025/2026
        ("2025/2026", Decimal('0.00'), Decimal('237100.00'), Decimal('0.00'), Decimal('18')),
        ("2025/2026", Decimal('237100.01'), Decimal('370500.00'), Decimal('42678.00'), Decimal('26')),
        ("2025/2026", Decimal('370500.01'), Decimal('512800.00'), Decimal('77362.00'), Decimal('31')),
        ("2025/2026", Decimal('512800.01'), Decimal('673000.00'), Decimal('121475.00'), Decimal('36')),
        ("2025/2026", Decimal('673000.01'), Decimal('857900.00'), Decimal('179147.00'), Decimal('39')),
        ("2025/2026", Decimal('857900.01'), Decimal('1817000.00'), Decimal('251258.00'), Decimal('41')),
        ("2025/2026", Decimal('1817000.01'), None, Decimal('644489.00'), Decimal('45')),
    ]

    for year, lower, upper, base, rate in brackets:
        TaxBracket.objects.create(
            tax_year=year,
            lower_limit=lower,
            upper_limit=upper,
            base_tax=base,
            marginal_rate=rate
        )

def unseed_tax_brackets(apps, schema_editor):
    TaxBracket = apps.get_model('payroll', 'TaxBracket')
    TaxBracket.objects.filter(tax_year__in=["2024/2025", "2025/2026"]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0005_taxbracket'),  
    ]

    operations = [
        migrations.RunPython(seed_tax_brackets, unseed_tax_brackets),
    ]
