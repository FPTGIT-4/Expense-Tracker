# Generated manually - category_type field with expense/income choices
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0005_delete_label'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='category',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='category',
            name='category_type',
            field=models.CharField(
                choices=[('expense', 'Expense'), ('income', 'Income')],
                default='expense',
                max_length=10,
                verbose_name='Type',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('user', 'name', 'category_type')},
        ),
    ]
