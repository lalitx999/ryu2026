"""Repair the legacy database and add guest/level-aware game rankings.

Some production databases record migration 0002 as applied but do not contain
the game_scores table.  This migration is intentionally idempotent so those
databases can recover without modifying users, courses, or enrollments.
"""

import django.db.models.deletion
from django.db import migrations, models


def ensure_game_scores_table(apps, schema_editor):
    connection = schema_editor.connection
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        existing_tables = connection.introspection.table_names(cursor)
        if 'game_scores' not in existing_tables:
            cursor.execute(
                "CREATE TABLE game_scores ("
                "id INT(10) UNSIGNED NOT NULL AUTO_INCREMENT, "
                "user_id INT(10) UNSIGNED NULL, "
                "player_name VARCHAR(50) NOT NULL DEFAULT '', "
                "game_mode VARCHAR(50) NOT NULL DEFAULT 'kana', "
                "jlpt_level VARCHAR(2) NOT NULL DEFAULT 'N5', "
                "score INT NOT NULL DEFAULT 0, "
                "created_at DATETIME(6) NOT NULL, "
                "PRIMARY KEY (id), "
                "KEY game_scores_mode_level (game_mode, jlpt_level), "
                "KEY game_scores_user_id (user_id)"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )
            return

        description = connection.introspection.get_table_description(cursor, 'game_scores')
        columns = {column.name for column in description}
        if 'player_name' not in columns:
            cursor.execute("ALTER TABLE game_scores ADD COLUMN player_name VARCHAR(50) NOT NULL DEFAULT ''")
        if 'jlpt_level' not in columns:
            cursor.execute("ALTER TABLE game_scores ADD COLUMN jlpt_level VARCHAR(2) NOT NULL DEFAULT 'N5'")
        # Legacy user IDs are unsigned. This avoids an incompatible FK while
        # allowing guest scores to have no user ID.
        cursor.execute("ALTER TABLE game_scores MODIFY user_id INT(10) UNSIGNED NULL")


class Migration(migrations.Migration):
    dependencies = [('courses', '0003_ryutube')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ensure_game_scores_table, migrations.RunPython.noop)],
            state_operations=[
                migrations.AlterField(
                    model_name='gamescore', name='user',
                    field=models.ForeignKey(blank=True, db_column='user_id', db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='game_scores', to='users.user'),
                ),
                migrations.AddField(model_name='gamescore', name='player_name', field=models.CharField(blank=True, default='', max_length=50)),
                migrations.AddField(model_name='gamescore', name='jlpt_level', field=models.CharField(default='N5', max_length=2)),
            ],
        ),
    ]
