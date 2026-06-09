from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_correct_minimum_balances'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='dark_mode',
            field=models.BooleanField(
                default=True,
                help_text='Use the dark theme (default). Uncheck for light mode.',
            ),
        ),
    ]
