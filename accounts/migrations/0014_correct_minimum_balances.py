from django.db import migrations
from decimal import Decimal

def correct_thresholds(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    for acc in Account.objects.all():
        if acc.minimum_balance > acc.initial_balance:
            acc.minimum_balance = Decimal('0.00')
            # Bypass the _explicit_threshold_edit validation during migration
            acc._explicit_threshold_edit = True
            acc.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_remove_usersettings_budget_remaining_threshold_and_more'),
    ]

    operations = [
        migrations.RunPython(correct_thresholds),
    ]
