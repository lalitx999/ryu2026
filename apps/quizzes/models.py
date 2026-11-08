from django.db import models
from django.conf import settings
from courses.models import Lesson

class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes', db_column='lesson_id')
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quizzes'

    def __str__(self):
        return f"{self.title} (Lesson: {self.lesson.title})"

class QuizQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', db_column='quiz_id')
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    explanation = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quiz_questions'

    def __str__(self):
        return f"Q{self.id} for Quiz: {self.quiz.title}"

class QuizAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts', db_column='user_id')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts', db_column='quiz_id')
    score = models.IntegerField()
    total_questions = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quiz_attempts'

    def __str__(self):
        return f"Attempt {self.id}: {self.user.email} -> {self.score}/{self.total_questions}"

class Vocabulary(models.Model):
    id = models.AutoField(primary_key=True)
    kanji = models.CharField(max_length=100)
    reading = models.CharField(max_length=100)
    meaning = models.CharField(max_length=255)
    level_name = models.CharField(max_length=20, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='easy')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vocabulary'

    def __str__(self):
        return f"{self.kanji} ({self.reading}) - {self.meaning}"

