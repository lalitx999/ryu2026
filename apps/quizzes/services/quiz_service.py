from core.http import ServiceError
from quizzes.models import Quiz, QuizAttempt, QuizQuestion


def quiz_for_lesson(lesson_id):
    quiz = Quiz.objects.filter(lesson_id=lesson_id).first()
    if not quiz:
        raise ServiceError("ไม่พบแบบฝึกหัดสำหรับบทเรียนนี้", status=404)
    questions = QuizQuestion.objects.filter(quiz=quiz).order_by("id").values(
        "id", "question_text", "option_a", "option_b", "option_c", "option_d")
    return {"quiz_id": quiz.id, "quiz_title": quiz.title, "questions": list(questions)}


def grade(user, quiz_id, answers):
    quiz = Quiz.objects.filter(id=quiz_id).first()
    if not quiz:
        raise ServiceError("ไม่พบแบบฝึกหัด", status=404)
    questions = list(QuizQuestion.objects.filter(quiz=quiz).order_by("id"))
    score, details = 0, []
    for q in questions:
        chosen = (answers or {}).get(str(q.id))
        correct = chosen == q.correct_option
        score += correct
        details.append({"question_id": q.id, "question_text": q.question_text, "chosen": chosen,
                        "correct_option": q.correct_option, "is_correct": correct, "explanation": q.explanation or ""})
    total = len(questions)
    attempt = QuizAttempt.objects.create(user=user, quiz=quiz, score=score, total_questions=total)
    return {"attempt_id": attempt.id, "score": score, "total_questions": total,
            "percentage": int(score / total * 100) if total else 0, "details": details}
