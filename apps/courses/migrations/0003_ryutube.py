"""Create the public Ryutube library safely on the legacy MySQL schema."""

import django.db.models.deletion
from django.db import migrations, models


def ensure_ryutube_tables(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
        if 'ryutube_categories' not in tables:
            cursor.execute(
                "CREATE TABLE ryutube_categories ("
                "id INT NOT NULL AUTO_INCREMENT, name VARCHAR(100) NOT NULL, "
                "slug VARCHAR(120) NOT NULL, sort_order INT NOT NULL DEFAULT 0, "
                "is_active TINYINT(1) NOT NULL DEFAULT 1, PRIMARY KEY (id), UNIQUE KEY ryutube_categories_slug (slug)"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )
        if 'ryutube_videos' not in tables:
            cursor.execute(
                "CREATE TABLE ryutube_videos ("
                "id INT NOT NULL AUTO_INCREMENT, title VARCHAR(255) NOT NULL, slug VARCHAR(255) NOT NULL, "
                "description LONGTEXT NOT NULL, video_url LONGTEXT NOT NULL, thumbnail VARCHAR(500) NOT NULL DEFAULT '', "
                "is_published TINYINT(1) NOT NULL DEFAULT 0, published_at DATETIME(6) NULL, sort_order INT NOT NULL DEFAULT 0, "
                "created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL, "
                "category_id INT NULL, linked_course_id INT(10) UNSIGNED NULL, "
                "PRIMARY KEY (id), UNIQUE KEY ryutube_videos_slug (slug), "
                "KEY ryutube_videos_category_id (category_id), KEY ryutube_videos_linked_course_id (linked_course_id)"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )


class Migration(migrations.Migration):
    dependencies = [('courses', '0002_gamescore_note')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ensure_ryutube_tables, migrations.RunPython.noop)],
            state_operations=[
                migrations.CreateModel(
                    name='RyutubeCategory',
                    fields=[
                        ('id', models.AutoField(primary_key=True, serialize=False)),
                        ('name', models.CharField(max_length=100)),
                        ('slug', models.SlugField(max_length=120, unique=True)),
                        ('sort_order', models.IntegerField(default=0)),
                        ('is_active', models.BooleanField(default=True)),
                    ],
                    options={'db_table': 'ryutube_categories', 'ordering': ('sort_order', 'name'), 'verbose_name': 'หมวด Ryutube', 'verbose_name_plural': 'หมวด Ryutube'},
                ),
                migrations.CreateModel(
                    name='RyutubeVideo',
                    fields=[
                        ('id', models.AutoField(primary_key=True, serialize=False)),
                        ('title', models.CharField(max_length=255)),
                        ('slug', models.SlugField(max_length=255, unique=True)),
                        ('description', models.TextField(blank=True, default='')),
                        ('video_url', models.TextField(help_text='YouTube URL or embed URL')),
                        ('thumbnail', models.CharField(blank=True, default='', max_length=500)),
                        ('is_published', models.BooleanField(default=False)),
                        ('published_at', models.DateTimeField(blank=True, null=True)),
                        ('sort_order', models.IntegerField(default=0)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('category', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='videos', to='courses.ryutubecategory')),
                        ('linked_course', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ryutube_videos', to='courses.course')),
                    ],
                    options={'db_table': 'ryutube_videos', 'ordering': ('-published_at', 'sort_order', '-created_at'), 'verbose_name': 'วิดีโอ Ryutube', 'verbose_name_plural': 'วิดีโอ Ryutube'},
                ),
            ],
        ),
    ]
