"""Machine-readable site metadata: structured data, robots, sitemap, web-app manifest."""
import json

from django.conf import settings
from django.templatetags.static import static

SITE_NAME = "RyuClass"
SITEMAP_ROUTES = [("/", "daily", "1.0"), ("/ryutube/", "weekly", "0.9"), ("/salepage/", "weekly", "0.8"),
                  ("/araigogu/", "weekly", "0.8"), ("/community/", "weekly", "0.8"), ("/games/", "weekly", "0.8"),
                  ("/guide/", "weekly", "0.8")]
COURSES = [("N5", "พื้นฐานตัวอักษร ฮิรางานะ คาตากานะ คันจิ และไวยากรณ์", "PT40H"),
           ("N4", "รูปประโยคเงื่อนไข การฟังสนทนา และคันจิ N4", "PT45H"),
           ("N3", "ไวยากรณ์ระดับกลาง Keigo และการอ่านจับใจความยาว", "PT50H"),
           ("N2", "สำนวนทางการสำหรับการทำงานบริษัทญี่ปุ่นและล่าม", "PT60H"),
           ("N1", "ขั้นสูงสุดสำหรับการแปลเอกสารและสอบชิงทุน", "PT70H")]
FAQ = [("RyuClass สอนคอร์สภาษาญี่ปุ่นระดับไหนบ้าง?",
        "RyuClass สอนครอบคลุมทุกระดับตั้งแต่ JLPT N5, N4, N3, N2 ถึง N1 พร้อมแบบฝึกหัดข้อสอบจำลอง วิดีโอ HD และไฟล์ PDF"),
       ("เงื่อนไขสิทธิ์การเรียนตลอดชีพ (Lifetime Access) เป็นอย่างไร?",
        "สะสมยอดชำระในระบบครบเกณฑ์ ฿10,000 (N5), ฿20,000 (N4), ฿30,000 (N3), ฿40,000 (N2), หรือ ฿50,000 (N1) จะได้รับสิทธิ์ปลดล็อกเรียนตลอดชีพให้อัตโนมัติ"),
       ("Araigogu AI คืออะไร?",
        "Araigogu AI คือระบบผู้ช่วยสอนภาษาญี่ปุ่นปัญญาประดิษฐ์ใน RyuClass ช่วยตรวจไวยากรณ์ วิเคราะห์ข้อสอบ และซ้อมบทสนทนาภาษาญี่ปุ่นส่วนตัว"),
       ("สามารถทดลองเรียนฟรีได้หรือไม่?",
        "สามารถเข้าเรียนทดลองฟรีบทเรียนพื้นฐาน N5 ได้ที่หน้า Ryutube โดยไม่มีค่าใช้จ่าย")]


def structured_data():
    base = settings.SITE_URL.rstrip("/")
    org = {"@context": "https://schema.org", "@type": "EducationalOrganization", "name": SITE_NAME,
           "alternateName": "ริวคลาส ภาษาญี่ปุ่นออนไลน์", "url": base, "logo": base + static("assets/ryu_logo.jpg"),
           "description": "แพลตฟอร์มเรียนภาษาญี่ปุ่นออนไลน์และเตรียมสอบวัดระดับ JLPT N5 - N1 ครบวงจร พร้อมระบบ AI Tutor Araigogu และสิทธิ์เรียนตลอดชีพ",
           "offers": {"@type": "AggregateOffer", "priceCurrency": "THB", "lowPrice": "0", "highPrice": "50000", "offerCount": "5"}}
    courses = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": i, "item": {
            "@type": "Course", "name": f"คอร์สเรียนภาษาญี่ปุ่น JLPT {lvl}", "description": f"คอร์สเรียนภาษาญี่ปุ่นระดับ {lvl} {desc}",
            "provider": {"@type": "Organization", "name": SITE_NAME, "sameAs": base},
            "hasCourseInstance": {"@type": "CourseInstance", "courseMode": "online", "courseWorkload": hours}}}
        for i, (lvl, desc, hours) in enumerate(COURSES, start=1)]}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
    return [org, courses, faq]


def dumps_safe(obj):
    """JSON for an inline <script>: '<' is escaped so the payload can never close the tag."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


def robots_txt():
    base = settings.SITE_URL.rstrip("/")
    ai_bots = ["GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-Web", "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot"]
    lines = ["User-agent: *", "Allow: /", "Disallow: /admin-panel/", "Disallow: /api/", ""]
    lines += [f"User-agent: {b}" for b in ai_bots]
    lines += ["Allow: /", "Allow: /llms.txt", "Allow: /llms-full.txt", "Disallow: /admin-panel/", "Disallow: /api/", "", f"Sitemap: {base}/sitemap.xml", ""]
    return "\n".join(lines)


def sitemap_xml():
    base = settings.SITE_URL.rstrip("/")
    items = "".join(f"<url><loc>{base}{path}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
                    for path, freq, prio in SITEMAP_ROUTES)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'


def manifest():
    icon = static("assets/ryuonline.png")
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    return {"name": "Ryuclass: เรียนภาษาญี่ปุ่นกับพี่ริว", "short_name": "Ryuclass",
            "description": "เรียนภาษาญี่ปุ่นออนไลน์กับพี่ริว เริ่มจาก 0 จนถึง N1 สอบติดจริง", "start_url": "/", "display": "standalone",
            "background_color": "#FEF9F0", "theme_color": "#FAAC68", "orientation": "portrait", "scope": "/",
            "icons": [{"src": icon, "sizes": f"{n}x{n}", "type": "image/png",
                       **({"purpose": "any maskable"} if n == 192 else {"purpose": "maskable"} if n == 512 else {})} for n in sizes]}


SERVICE_WORKER = """// Required for PWA installability; intentionally does not intercept fetches.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(clients.claim()));
self.addEventListener('fetch', () => {});
"""
