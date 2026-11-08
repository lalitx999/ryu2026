from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='is_renewal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='payment',
            name='discount_percent',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
