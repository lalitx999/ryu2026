import re

from django.db import migrations, models


LEVELS = ('N5', 'N4', 'N3', 'N2', 'N1')


def populate_course_levels(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    for course in Course.objects.all().only('id', 'title', 'slug'):
        text = f'{course.title or ""} {course.slug or ""}'.upper()
        match = re.search(r'(?<![A-Z0-9])N([1-5])(?![A-Z0-9])', text)
        # Existing production courses historically used IDs 1–5.  This is a
        # one-time migration fallback only; runtime code does not use IDs.
        level = f'N{match.group(1)}' if match else (f'N{6 - course.id}' if course.id in range(1, 6) else 'N5')
        if level in LEVELS:
            Course.objects.filter(pk=course.pk).update(level=level)


class Migration(migrations.Migration):
    dependencies = [('courses', '0007_lesson_pdf_file_lesson_pdf_title')]

    operations = [
        migrations.AddField(
            model_name='course',
            name='level',
            field=models.CharField(choices=[(level, level) for level in LEVELS], db_index=True, default='N5', max_length=2),
        ),
        migrations.RunPython(populate_course_levels, migrations.RunPython.noop),
    ]
