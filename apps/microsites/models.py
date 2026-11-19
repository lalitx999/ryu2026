"""RYU Network content that lives in the database (only RYU KANJI so far)."""
from django.conf import settings
from django.db import models


class Kanji(models.Model):
    """One JLPT kanji.  Readings / English meanings / stroke paths come from open data (KANJIDIC2, Waller JLPT lists,
    KanjiVG); the Thai fields are drafted by AI and reviewed by a teacher in the admin panel."""

    LEVELS = [(lv, lv) for lv in ("N5", "N4", "N3", "N2", "N1")]
    AI_NONE, AI_DRAFT, AI_APPROVED = "none", "draft", "approved"
    AI_STATUS = [(AI_NONE, "ยังไม่มีภาษาไทย"), (AI_DRAFT, "ร่างจาก AI รอตรวจ"), (AI_APPROVED, "ผู้สอนตรวจแล้ว")]

    char = models.CharField(max_length=4, unique=True)
    level = models.CharField(max_length=2, choices=LEVELS, db_index=True)
    sort = models.PositiveIntegerField(default=0, db_index=True)           # order inside a level (by frequency)
    stroke_count = models.PositiveSmallIntegerField(default=0)
    frequency = models.PositiveIntegerField(null=True, blank=True)         # newspaper frequency rank (KANJIDIC2)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)        # Japanese school grade
    on_readings = models.JSONField(default=list, blank=True)               # hiragana as in KANJIDIC2; shown in katakana
    kun_readings = models.JSONField(default=list, blank=True)              # "ひと.つ": okurigana after the dot
    meanings_en = models.JSONField(default=list, blank=True)
    stroke_paths = models.JSONField(default=list, blank=True)              # KanjiVG path "d" strings, in stroke order

    th_meaning = models.CharField(max_length=255, blank=True)
    th_note = models.TextField(blank=True)                                 # memory tip / usage note
    examples = models.JSONField(default=list, blank=True)                  # [{"word", "reading", "th"}]
    ai_status = models.CharField(max_length=10, choices=AI_STATUS, default=AI_NONE, db_index=True)
    ai_model = models.CharField(max_length=80, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ryu_kanji"
        ordering = ["sort"]

    def __str__(self):
        return f"{self.char} ({self.level})"
