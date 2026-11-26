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
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                    db_constraint=False)  # legacy users.id is INT UNSIGNED: no DB-level FK
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ryu_kanji"
        ordering = ["sort"]

    def __str__(self):
        return f"{self.char} ({self.level})"


class DictEntry(models.Model):
    """One JMdict word (common-words edition).  Japanese forms, parts of speech and English glosses are open data
    (JMdict, CC BY-SA); the Thai fields are written by AI on first lookup (or in advance for the most basic words)."""

    AI_NONE, AI_DRAFT, AI_APPROVED = "none", "draft", "approved"
    AI_STATUS = [(AI_NONE, "ยังไม่มีภาษาไทย"), (AI_DRAFT, "AI ช่วยอธิบาย"), (AI_APPROVED, "ผู้สอนตรวจแล้ว")]

    jmdict_id = models.PositiveIntegerField(unique=True)
    headword = models.CharField(max_length=64, db_index=True)      # first kanji form, or the reading for kana words
    reading = models.CharField(max_length=64, db_index=True)
    forms = models.JSONField(default=list, blank=True)            # all kanji spellings, common first
    readings = models.JSONField(default=list, blank=True)
    senses = models.JSONField(default=list, blank=True)           # [{"pos": [...], "g": [english...], "m": [misc...]}]
    rank = models.PositiveIntegerField(default=0, db_index=True)   # lower = more basic (see data/README.md)
    keys = models.TextField(blank=True)                           # "|日本|にほん|にっぽん|" for exact / prefix lookups
    gloss_text = models.TextField(blank=True)                     # lowercase English glosses for English search

    th_gloss = models.CharField(max_length=255, blank=True)
    th_explain = models.TextField(blank=True)
    examples = models.JSONField(default=list, blank=True)         # [{"ja", "reading", "th"}]
    ai_status = models.CharField(max_length=10, choices=AI_STATUS, default=AI_NONE, db_index=True)
    ai_model = models.CharField(max_length=80, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ryu_dict_entry"
        ordering = ["rank"]

    def __str__(self):
        return f"{self.headword} ({self.reading})"


class DictThaiQuery(models.Model):
    """Cache of "Thai word -> Japanese words" answers from AI, so each Thai query is asked only once."""

    query = models.CharField(max_length=100, unique=True)
    entry_ids = models.JSONField(default=list, blank=True)        # matched DictEntry ids, best first
    suggestions = models.JSONField(default=list, blank=True)      # AI words not found in the dictionary
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ryu_dict_thai_query"


class TranslationCache(models.Model):
    """Finished AI translations, keyed by a hash of (text, direction, style), so a repeated request costs nothing.
    Only the result is stored (it contains the meaning of the text, so it is purged after 30 days by a daily task)."""

    key = models.CharField(max_length=64, unique=True)
    direction = models.CharField(max_length=8)                    # th2ja | ja2th
    style = models.CharField(max_length=10)                       # casual | polite | business
    result = models.JSONField(default=dict)
    hits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ryu_translation_cache"


class ExamItem(models.Model):
    """One mock-JLPT question written by AI in the JLPT style (never copied from real tests), kept only if a second AI
    pass solved it to the same answer.  Published with an "AI mock question" label; teachers approve, fix or hide."""

    SECTIONS = [("vocab", "คำศัพท์"), ("kanji", "คันจิ"), ("grammar", "ไวยากรณ์"), ("reading", "การอ่าน"), ("listening", "การฟัง")]
    LIVE, APPROVED, HIDDEN = "live", "approved", "hidden"
    STATUS = [(LIVE, "ใช้งาน (AI)"), (APPROVED, "ผู้สอนตรวจแล้ว"), (HIDDEN, "ซ่อน")]

    level = models.CharField(max_length=2, choices=Kanji.LEVELS, db_index=True)
    section = models.CharField(max_length=10, choices=SECTIONS, db_index=True)
    group = models.CharField(max_length=40, blank=True, db_index=True)   # questions sharing one passage / script
    passage = models.TextField(blank=True)                              # reading text, or listening script (read aloud)
    stem = models.TextField()                                           # 【...】 marks the underlined part
    choices = models.JSONField(default=list)
    answer = models.PositiveSmallIntegerField()
    explanation = models.TextField(blank=True)                          # Thai
    status = models.CharField(max_length=10, choices=STATUS, default=LIVE, db_index=True)
    reports = models.PositiveIntegerField(default=0)
    ai_model = models.CharField(max_length=80, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                    db_constraint=False)  # legacy users.id is INT UNSIGNED: no DB-level FK
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ryu_exam_item"
        ordering = ["level", "section", "id"]

    def __str__(self):
        return f"{self.level} {self.section} #{self.pk}"
