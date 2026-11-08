from decimal import Decimal
from django.db import migrations, models
from django.core.validators import MinValueValidator


def seed_prices(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    # Copy the previous checkout prices once; monthly prices already live in DB.
    prices = {1: (5000, 9000, 10000), 2: (6500, 12000, 20000),
              3: (8000, 15000, 30000), 4: (9500, 18000, 40000), 5: (11000, 21000, 50000)}
    for pk, (half_year, year, lifetime) in prices.items():
        Course.objects.using(schema_editor.connection.alias).filter(pk=pk).update(
            price_180=half_year, price_365=year, price_lifetime=lifetime)


class Migration(migrations.Migration):
    dependencies = [('courses', '0004_gamescore_guest_and_level')]
    operations = [
        migrations.AlterField(model_name='course', name='price', field=models.DecimalField('ราคารายเดือน (30 วัน)', max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(Decimal('0.01'))])),
        *[migrations.AddField(model_name='course', name=name, field=models.DecimalField(label, max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))], help_text='เว้นว่างเพื่อปิดแพ็กเกจ')) for name, label in [('price_180', 'ราคา 6 เดือน (180 วัน)'), ('price_365', 'ราคา 1 ปี (365 วัน)'), ('price_lifetime', 'ราคาตลอดชีพ')]],
        migrations.RunPython(seed_prices, migrations.RunPython.noop),
    ]
