"""AI chat runs in Celery: DeepSeek first, Groq as fallback.  The request only enqueues and polls."""
from celery import shared_task

from support import ai

PERSONA = ('คุณคือ "AIRIS" (Artificial Intelligence Ryuso Instruction System) 🇯🇵 ระบบผู้ช่วยสอนภาษาญี่ปุ่นปัญญาประดิษฐ์ประจำ RyuClass\n'
           '== บุคลิก ==\n- ใจดี รอบรู้ เป็นกันเอง แทนตัวเองว่า "AIRIS" หรือ "หนู"\n'
           '- พูดภาษาไทยเป็นหลัก แทรกคำภาษาญี่ปุ่นพร้อมคำแปล ใช้ Emoji พอประมาณ\n')

GENERAL = (PERSONA + "== บทบาท ==\n1. แนะนำคอร์ส N5-N1 และวิธีสมัคร (ราคาอยู่ในหน้าคอร์ส)\n"
           "2. สอนไวยากรณ์ คันจิ คำศัพท์พร้อมตัวอย่างประโยค\n"
           "3. สะสมยอดเรียน 10k/20k/30k/40k/50k ปลดล็อก Lifetime N5/N4/N3/N2/N1")

LESSON = (PERSONA + "== กฎ ==\n1. ห้ามแนะนำให้สมัครคอร์ส 2. ห้ามพูดถึงราคา 3. เน้นอธิบายไวยากรณ์ภาษาญี่ปุ่น\n"
          "นักเรียนกำลังเรียนบท: {lesson} ระดับ: {level}\nตอบเฉพาะเรื่องภาษาญี่ปุ่นและเนื้อหาบทเรียนนี้")


@shared_task
def chat_reply(messages, lesson_title="", course_level=""):
    system = LESSON.format(lesson=lesson_title, level=course_level) if lesson_title else GENERAL
    payload = [{"role": "system", "content": system}]
    for m in messages[-20:]:  # cap history sent upstream
        role = "assistant" if m.get("role") in ("bot", "assistant") else "user"
        payload.append({"role": role, "content": str(m.get("content", ""))[:2000]})
    result = ai.complete(payload, max_tokens=800, timeout=25)
    if result:
        return {"reply": result.text}
    return {"reply": "ขออภัยด้วยค่ะ ตอนนี้ AIRIS ยังไม่ได้เชื่อมต่อบริการ AI (ตั้งค่า DEEPSEEK_API_KEY / GROQ_API_KEY ใน .env) 💖"}


FALLBACK_REPLY = ("ขออภัยด้วยครับ ปัจจุบันระบบขัดข้องชั่วคราว ไม่สามารถดึงข้อมูลจาก AI Engine "
                  "(DeepSeek / Groq) ได้ในขณะนี้ 💖")


@shared_task
def araigogu_reply(session_pk):
    """Build the prompt from the stored history, call the LLM, store and return the assistant message."""
    from support.models import AraigoguMessage, AraigoguSession
    from support.services.araigogu_prompts import system_prompt

    sess = AraigoguSession.objects.get(pk=session_pk)
    history = list(AraigoguMessage.objects.filter(session=sess).order_by("-created_at").values_list("sender", "content")[:20])[::-1]
    payload = [{"role": "system", "content": system_prompt(sess.target_language, sess.mode)}]
    payload += [{"role": "assistant" if s == "assistant" else "user", "content": c} for s, c in history]
    result = ai.complete(payload)
    text, model, tokens = (result.text, result.model, result.tokens) if result else (FALLBACK_REPLY, "fallback", 0)
    AraigoguMessage.objects.create(session=sess, sender="assistant", content=text, model_used=model[:50], tokens_used=tokens)
    sess.save(update_fields=["updated_at"])
    return {"session_id": sess.session_id, "content": text, "model_used": model, "target_language": sess.target_language,
            "mode": sess.mode}
