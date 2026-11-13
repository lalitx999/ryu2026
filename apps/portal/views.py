"""Page views for the XP desktop.  They render shells; data is loaded through the AJAX endpoints."""
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from courses.models import Course
from portal import seo
from courses.selectors import course_selector
from users.selectors.user_selector import profile_payload

LIBRARY_LEVELS = [
    ("N5", "คอร์สปูพื้นฐาน N5", "ชีทคำศัพท์ คันจิพื้นฐาน 100 ตัว และแบบฝึกหัด Minna no Nihongo / Marugoto", "accent-n5"),
    ("N4", "คอร์สระดับต้น-กลาง N4", "สรุปไวยากรณ์ผันกริยา คำศัพท์ใช้บ่อย 1,500 คำ และชีทบทสนทนาชีวิตประจำวัน", "accent-n4"),
    ("N3", "คอร์สระดับกลาง N3", "ชีทสรุป Try! N3 ไวยากรณ์เชื่อมโยง และคลังหนังสือแนะนำเตรียมสอบ", "accent-n3"),
    ("N2", "คอร์สระดับกลางสูง N2", "เจาะลึกข้อสอบการอ่าน ไวยากรณ์เชิงเปรียบเทียบ และบทความธุรกิจ", "accent-n2"),
    ("N1", "คอร์สระดับสูง N1", "คันจิชั้นสูง สำนวนวรรณกรรม และชีทตะลุยโจทย์ระดับยากที่สุด", "accent-n1"),
]


@ensure_csrf_cookie
def home(request):
    user = request.user if request.user.is_authenticated else None
    courses = course_selector.catalog(user)
    profile = profile_payload(user) if user else None
    # Server-render the first paint (catalogue + profile) so the desktop never flashes empty;
    # the same data is handed to desktop.js through json_script (no extra request on load).
    return render(request, "portal/home.html", {
        "courses": courses,
        "my_courses": [c for c in courses if c["has_access"]],
        "profile": profile,
        "boot": {"loggedIn": bool(user), "profile": profile, "courses": courses},
    })


GUIDE_STEPS = [
    (1, "ขั้นตอนการสมัครและแจ้งสลิปชำระเงิน",
     "กดปุ่ม <b>\"เข้าสู่ระบบ / สมัครเรียน\"</b> บนแถบด้านบน หรือเลือกคอร์สที่ต้องการ กรอกข้อมูลสมัครพร้อมแนบไฟล์สลิปโอนเงิน "
     "(ธ.ทหารไทยธนชาต ttb เลขบัญชี 612-2-76925-7 บจก. ออโต้บอทยูเอ จำกัด) ระบบจะตรวจสอบและอนุมัติสิทธิ์ให้อัตโนมัติหรือภายใน 24 ชม."),
    (2, "การเข้าเรียนสดผ่าน Zoom",
     "ชั้นเรียนสดจะจัดขึ้นผ่าน Zoom ทุกสัปดาห์ ลิงก์ห้องเรียน Zoom จะถูกส่งในกลุ่ม LINE Support ประจำคลาส ก่อนเริ่มเรียน 15 นาที"),
    (3, "การดูคลิปย้อนหลังและทำแบบฝึกหัด",
     "เมื่อเข้าสู่ระบบแล้ว ให้ไปที่ <b>\"คอร์สเรียนของฉัน\"</b> คลิกเลือกวิชาที่ต้องการ สามารถเปิดเล่นวิดีโอย้อนหลังและกดทำแบบฝึกหัดทบทวนหลังบทเรียนเพื่อประเมินตนเองได้ทันที"),
]


@ensure_csrf_cookie
def guide(request):
    return render(request, "portal/guide.html", {"steps": GUIDE_STEPS})


@ensure_csrf_cookie
def library(request):
    return render(request, "portal/library.html", {"levels": LIBRARY_LEVELS})


@ensure_csrf_cookie
def ryutube(request):
    return render(request, "portal/ryutube.html", {"lessons": course_selector.free_trial_lessons()})


@ensure_csrf_cookie
def course_page(request, course_id):
    get_object_or_404(Course, pk=course_id, is_active=True)
    outline = course_selector.course_outline(course_id, request.user)
    # the sign-in / payment dialogs on this page read the same #ryu-boot payload as the desktop
    boot = {"loggedIn": request.user.is_authenticated, "profile": None, "courses": course_selector.catalog(request.user if request.user.is_authenticated else None)}
    mine = next((c for c in boot["courses"] if c["id"] == course_id), None)
    access = mine if mine and (mine["access_lifetime"] or mine["access_until"]) else None   # expiry shown in the banner
    return render(request, "portal/course.html", {"outline": outline, "course_id": course_id, "boot": boot, "access": access})


# ───────────────────────────── sale page / SEO / PWA ─────────────────────────────
LIFETIME_LABELS = {"N5": "N5", "N4": "N5-N4", "N3": "N5-N4-N3", "N2": "N5-N4-N3-N2", "N1": "N5-N4-N3-N2-N1"}


def salepage(request):
    """Public landing page.  The price table is read from the live course prices (one query)."""
    rows = []
    for c in Course.objects.filter(is_active=True).only("level", "price", "price_180", "price_365", "price_lifetime").order_by("sort_order", "id"):
        monthly = c.price or 0
        rows.append({
            "level": c.level, "monthly": monthly, "six": c.price_180, "twelve": c.price_365, "lifetime": c.price_lifetime,
            "six_saving": monthly * 6 - c.price_180 if c.price_180 else None,
            "twelve_saving": monthly * 12 - c.price_365 if c.price_365 else None,
            "label": LIFETIME_LABELS.get(c.level, c.level),
        })
    return render(request, "portal/salepage.html", {
        "rows": rows, "levels": ["N1", "N2", "N3", "N4"],
        "features": [("sa.png", "ระบบการสอนแบบ Zoom", "เรียนสดผ่าน Zoom"), ("sss.png", "ระบบการเรียนบน Teachable", "ระบบ Teachable"),
                     ("asasa.png", "กลุ่ม LINE ส่วนตัว", "กลุ่ม LINE เฉพาะ"), ("86-1-1024x1024.png", "ครบทุกคอร์ส JLPT", "ครบทุกเลเวล")],
    })


def register_redirect(request):
    """Legacy /auth/register?level=N3 links: the sign-up form lives in the desktop's auth dialog."""
    level = request.GET.get("level", "")
    suffix = f"&level={level}" if level in ("N1", "N2", "N3", "N4", "N5") else ""
    return HttpResponseRedirect(f"/?auth=register{suffix}")


def robots_txt(request):
    return HttpResponse(seo.robots_txt(), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    return HttpResponse(seo.sitemap_xml(), content_type="application/xml; charset=utf-8")


def manifest_json(request):
    return JsonResponse(seo.manifest(), json_dumps_params={"ensure_ascii": False}, content_type="application/manifest+json")


def service_worker(request):
    resp = HttpResponse(seo.SERVICE_WORKER, content_type="application/javascript; charset=utf-8")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def llms_txt(request, name):
    """AI-crawler summaries (llms.txt / llms-full.txt); llm*.txt kept as aliases like the legacy site."""
    from django.contrib.staticfiles import finders
    path = finders.find("seo/" + ("llms-full.txt" if "full" in name else "llms.txt"))
    if not path:
        raise Http404
    with open(path, encoding="utf-8") as fh:
        return HttpResponse(fh.read(), content_type="text/plain; charset=utf-8")
