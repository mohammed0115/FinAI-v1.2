from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_organization_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='google_id',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='facebook_id',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='social_provider',
            field=models.CharField(
                blank=True,
                choices=[('google', 'Google'), ('facebook', 'Facebook'), ('email', 'Email')],
                max_length=20,
                null=True,
            ),
        ),
    ]
