# RyuClass — Pure Django 5 + Bootstrap 5.3 (local) + AJAX + MySQL

อัปเกรดจาก `ryu_new` (Next.js + DRF/JWT) เป็น Django ล้วน — UI แบบ Windows XP เดิม, Bootstrap 5.3.8 โฮสต์เอง (ไม่มี CDN), AJAX ด้วย `fetch`, ฐานข้อมูล MySQL (ตารางเดิมใช้ต่อได้ทันที)

## รัน (dev)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # แก้ DB_*, SECRET_KEY
python manage.py migrate        # DB ใหม่
# DB เดิมที่ import จาก ryuclass_db.sql แล้ว:  python manage.py migrate --fake-initial
python manage.py createsuperuser
python manage.py runserver      # http://127.0.0.1:8000  ·  แอดมิน /admin-panel/
```
ไม่มี MySQL ในเครื่อง? ทดสอบ UI ด้วย SQLite: `DB_ENGINE=sqlite python manage.py migrate --run-syncdb`
Celery ใน `local.py` รัน task แบบ inline (EAGER) จึงไม่ต้องมี Redis ตอนพัฒนา

## Production
`DJANGO_SETTINGS_MODULE=config.settings.production`, `DEBUG=False`, `collectstatic`, WhiteNoise เสิร์ฟ `/static/`
(หรือให้ Nginx alias → `staticfiles/`), รัน worker: `celery -A config worker -l info` (ต้องมี Redis)

## โครงสร้าง (ตามกฎ Service/Selector)
```
config/settings/{base,local,production}.py   config/celery.py   config/urls.py
apps/<app>/{models.py, services/, selectors/, tasks.py, views.py, urls.py}
  core        ajax helpers (ok/fail/ajax_view), decorators, template tags
  users       login/register/verify/reset (session auth + legacy PHP bcrypt)
  courses     catalog/outline selectors, access/progress services, study calendar
  payments    payment_service (price check, intake, approve/reject), tasks (EasySlip, Telegram)
  quizzes     quiz_service
  support     AI chat + Araigogu (ai.py = DeepSeek→Groq client, tasks.py = Celery)
  community   กระทู้/ไลก์/คอมเมนต์ + AI moderation (Celery)      affiliates/system_config  models only
  portal      หน้า XP desktop, guide, library, ryutube, course player, salepage, SEO/PWA
  courses     (+ game_selector/game_service: RyuGames leaderboard)
  backoffice  แอดมินแบบ Bootstrap: dashboard, slip QC, คอร์ส/หมวด/บทเรียน (ลากจัดลำดับ, PDF), นักเรียน (+สิทธิ์รายคอร์ส,
              นำเข้า CSV), ยอดขาย (+export CSV), สถิติการเรียน, สิทธิ์, ตั้งค่าระบบ (+ค่าใน DB เฉพาะ superuser), broadcast,
              แจ้งเตือนต่ออายุ, ตรวจเนื้อหาชุมชน, คำร้อง, คำขอย้ายระบบ/รหัสเชิญตลอดชีพ, กฎ+ประวัติตรวจสลิป, รายละเอียดสลิป
static/vendor/bootstrap/   Bootstrap 5.3.8 (css + bundle.js)      static/css/xp.css  ธีม XP
static/js/{ajax,desktop,course,ambient,admin,admin_courses,admin_users,community,araigogu}.js  static/js/games/*.js
static/vendor/{three,confetti}/  (ในเครื่อง ไม่ใช้ CDN)   static/data/{games,speed_quiz}.json   tools/extract_game_data.mjs (สร้าง JSON จากซอร์สเดิม)
```
View ทำแค่ รับ request → เรียก service/selector → คืน JSON/render · งานช้า (EasySlip, Telegram, อีเมล, AI) อยู่ใน Celery
Query: catalogue = 3 queries ไม่ว่ามีกี่คอร์ส (annotate + group), outline = 4 queries, อนุมัติสลิป lock แถว (`select_for_update`) กันนับยอดซ้ำ

## พอร์ตแล้ว / ยังไม่พอร์ต
ครบทุกหน้าของระบบเดิมแล้ว: desktop XP, auth, สลิป/ต่ออายุ, โปรไฟล์, คอร์ส+player+quiz, Ryutube, คู่มือ, Library, AI chat,
**ชุมชน, Araigogu AI, RyuGames (6 เกม + Speed Quiz 3D), Salepage, robots/sitemap/manifest/sw/llms.txt/JSON-LD, แบนเนอร์ Halloween,
แอดมินครบ (courses/lessons/users/import/sales/analytics/roles/settings)**.
ยังไม่ได้ทดสอบกับของจริง: MySQL บนเซิร์ฟเวอร์, Celery+Redis, EasySlip/Telegram/DeepSeek/Groq (ต้องมี key) — ทดสอบด้วย SQLite + mock

## งานตั้งเวลา (production)
รัน `celery -A config worker -l info` **และ** `celery -A config beat -l info` — beat ส่งอีเมลเตือนต่ออายุทุกวัน 09:00 (เหลือ 3/2/1 วัน, กันส่งซ้ำรายวัน; ควรตั้ง CACHES เป็น Redis ให้ทุก worker ใช้ร่วมกัน)
สั่งมือ: `python manage.py send_renewal_reminders [--days 3 2 1] [--include-expired] [--dry-run]`

## ทดสอบ
`DB_ENGINE=sqlite python manage.py test` (68 เทสต์: สิทธิ์, XSS, ราคา, N+1 ด้วย assertNumQueries, moderation mock, ownership ของ Araigogu,
กันคะแนนเกมปลอม, CSV import/export, upload PDF) · `python manage.py seed_demo` สร้าง admin@test.local / student@test.local (รหัส demo12345, เฉพาะ DEBUG)
Python 3.14 + Django 5.0: เทสต์ที่ render template ใช้ shim `core/testing.py` (ไม่กระทบ production)

## ความแตกต่างที่ตั้งใจ
- JWT → Django session + CSRF (`X-CSRFToken` อ่านจาก cookie ใน `ajax.js`)
- สลิปไม่เสิร์ฟสาธารณะอีกต่อไป: `/api/payments/slip/<id>/` เฉพาะเจ้าของ/แอดมิน
- รีเซ็ตรหัสผ่าน (อีเมล+เบอร์) จำกัด 5 ครั้ง/15 นาที/อีเมล · แชต AI จำกัด 20 ข้อความ/นาที
- Wallpaper/พื้นหลัง Unsplash เดิมแทนด้วย CSS gradient ในเครื่อง; หิมะ/ซากุระใช้ canvas 2D แทน Three.js
- ชุมชน: โพสต์/คอมเมนต์ถูกคัดกรองใน Celery (สถานะ PENDING → APPROVED/REWRITTEN/REJECTED) แทนการรอ API ค้างในคำขอ; เจ้าของโพสต์เห็นโพสต์ที่รอตรวจของตัวเองเท่านั้น
- Araigogu: ประวัติสนทนาผูกกับเจ้าของ (ผู้ใช้หรือเบราว์เซอร์ของแขก) — ระบบเดิมให้ใครก็ได้ดู/ลบ session ทุกอัน
- เกม: เซิร์ฟเวอร์ตรวจโหมด/ระดับ/เพดานคะแนน + rate limit; Speed Quiz 3D ส่งคะแนนขึ้น Ranking Board (ของเดิมไม่ส่ง); ไม่ส่งคะแนน 0
- แอดมิน: ลบคอร์สได้เฉพาะที่ยังไม่มีนักเรียน/การชำระเงิน; สถิติและรายงานคำนวณจากข้อมูลจริง (ของเดิม hard-code); รหัสผ่านที่สุ่มให้ใช้ `secrets`
- Google Fonts/CDN ทั้งหมดถูกตัด: ใช้ฟอนต์ระบบ, Bootstrap/three.js/confetti เก็บใน `static/vendor/`
- Production: `config.storage.HashedModuleStorage` เขียน `import` ใน three.js ให้ชี้ไฟล์ที่มี hash (ตรวจแล้วกับ collectstatic)
- หน้าเรียน `/courses/<id>/`: ตัวเล่นเหมือนระบบเดิม (ซ่อนปุ่ม YouTube + แผ่นคลุม + แถบควบคุมเล่น/หยุด ±10 วิ เลื่อนเวลา เสียง ความเร็ว CC เต็มจอ, บทเรียนก่อนหน้า/ถัดไป, โน้ตแทรกเวลา [mm:ss] กดข้ามได้, ดาวน์โหลด .txt) — ใช้ YouTube IFrame API ผ่าน postMessage; เวลาเรียนที่บันทึกเป็นเวลาเล่นจริง; ปุ่ม "เรียนจบ" เลิกได้และเก็บใน DB (ของเดิมเก็บแค่ localStorage)
- PDF บทเรียน `/storage/protected_pdfs/<ไฟล์>`: เปิดได้เฉพาะแอดมิน บทเรียนฟรี หรือผู้มีสิทธิ์ในคอร์สนั้น (ของเดิมเสิร์ฟสาธารณะ)
- ราคาต่ออายุเฉพาะบุคคล (แอดมินตั้งในหน้านักเรียน) มีผลกับการต่ออายุจริงแล้ว: แทนราคาแพ็กเกจ 30 วันเฉพาะเมื่อกด "ต่ออายุ" (ได้ 30+3 วัน) — ของเดิมมีช่องนี้แต่ไม่เคยนำไปคิดราคา
- ฐานข้อมูล: migration ใหม่มีแค่ `community/0003` (เพิ่มตัวเลือกสถานะ PENDING — เปลี่ยนเฉพาะ choices ไม่มี SQL บน MySQL) ตารางอื่นใช้ `db_table` เดิมทั้งหมด จึงต่อกับ DB จริงด้วย `migrate --fake-initial` ได้
