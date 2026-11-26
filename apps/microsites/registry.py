"""The RYU Network: every extra domain, what it is for, and how it looks.

Pure data with no Django imports, so `config/settings` can read the host list for ALLOWED_HOSTS.
Thai domains are stored as people type them; `host` is the punycode form that browsers send in
the Host header (and that nginx / certbot / Cloudflare need).

A site whose `domain` has a path ("คันจิ.online/kana") has no domain of its own: it is served under
that path of its host site (see `mount`), and its host is not added to BY_HOST.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Microsite:
    key: str                # stable id: template name, ?site= preview, UTM campaign
    domain: str             # human form, e.g. "คันจิ.online", or "คันจิ.online/kana" for a mounted site
    kind: str               # "sales" (sales page) or "tool" (free tool, no login)
    name: str               # brand shown in the header, e.g. "RYU KANJI"
    title: str              # <title> / og:title
    description: str        # meta description
    tagline: str            # one line under the name on network cards
    icon: str               # icon name (microsites/templatetags/ryu_icons.py) or a text glyph like "漢"
    accent: str             # CSS colour for this site's theme
    live: bool = True       # False -> "coming soon" page until its phase ships
    keywords: tuple = field(default_factory=tuple)

    @property
    def host(self):
        return self.domain.split("/", 1)[0].encode("idna").decode("ascii")

    @property
    def mount(self):
        """Path this site lives under on its host site ("kana"), or "" for a site with its own domain."""
        return self.domain.partition("/")[2].strip("/")

    @property
    def url(self):
        return f"https://{self.host}/" + (f"{self.mount}/" if self.mount else "")


SITES = (
    Microsite(
        key="learn", domain="เรียนภาษาญี่ปุ่น.online", kind="sales", name="RYU CLASS",
        title="เรียนภาษาญี่ปุ่นออนไลน์ N5–N1 หลักสูตรครบ เรียนสด + ดูย้อนหลัง | RYU CLASS",
        description="หลักสูตรเรียนภาษาญี่ปุ่นออนไลน์ครบทุกระดับ JLPT N5 ถึง N1 เรียนสดผ่าน Zoom ทุกสัปดาห์ ดูคลิปย้อนหลัง เอกสาร PDF แบบฝึกหัด และกลุ่ม LINE ถามตอบ เลือกแพ็กเกจรายเดือนถึงตลอดชีพ",
        tagline="หลักสูตรเรียนภาษาญี่ปุ่น N5 → N1", icon="graduation", accent="#1d4ed8",
        keywords=("เรียนภาษาญี่ปุ่น", "คอร์สภาษาญี่ปุ่นออนไลน์", "เรียนภาษาญี่ปุ่นออนไลน์", "JLPT"),
    ),
    Microsite(
        key="japanese", domain="ภาษาญี่ปุ่น.online", kind="sales", name="RYU JAPANESE",
        title="ภาษาญี่ปุ่น เริ่มต้นยังไงดี? เส้นทางจากศูนย์ เรียนฟรีก่อนตัดสินใจ | RYU CLASS",
        description="อยากเก่งภาษาญี่ปุ่นเพื่อทำงาน เที่ยว ดูอนิเมะ หรือสอบทุน เริ่มจากตรงไหนดี? ดูเส้นทางเรียนภาษาญี่ปุ่นจากศูนย์ ลองเครื่องมือฟรี อักษร คันจิ พจนานุกรม และแบบวัดระดับ ก่อนเลือกคอร์สที่ใช่",
        tagline="เริ่มต้นภาษาญี่ปุ่นจากศูนย์", icon="globe", accent="#dc2626",
        keywords=("ภาษาญี่ปุ่น", "ภาษาญี่ปุ่นเบื้องต้น", "เริ่มเรียนภาษาญี่ปุ่น", "ภาษาญี่ปุ่นสำหรับผู้เริ่มต้น"),
    ),
    Microsite(
        key="ryu", domain="เรียนภาษาญี่ปุ่นกับพี่ริว.online", kind="sales", name="เรียนกับพี่ริว",
        title="เรียนภาษาญี่ปุ่นกับพี่ริว สอนสนุก เข้าใจง่าย จาก 0 สู่ N1 | Ryuso Sense",
        description="รู้จักพี่ริว (Ryuso Sense) ครูสอนภาษาญี่ปุ่นออนไลน์ สอนสดทุกสัปดาห์ เทคนิคจำง่าย ใช้ได้จริง ดูตัวอย่างการสอนฟรี และคุยกับพี่ริวได้โดยตรงทาง LINE",
        tagline="ครูสอนภาษาญี่ปุ่น Ryuso Sense", icon="user", accent="#ea580c",
        keywords=("พี่ริว", "Ryuso Sense", "ครูสอนภาษาญี่ปุ่น", "เรียนภาษาญี่ปุ่นกับพี่ริว"),
    ),
    Microsite(
        key="kana", domain="คันจิ.online/kana", kind="tool", name="RYU KANA",
        title="ฮิรางานะ คาตากานะ ตารางอักษรญี่ปุ่น พร้อมเสียงอ่านและแบบฝึก | RYU KANA",
        description="เรียนอักษรภาษาญี่ปุ่น ฮิรางานะ และคาตากานะ ฟรี ตารางครบ 104 เสียง พร้อมเสียงอ่าน คำศัพท์ตัวอย่าง ฝึกเขียน และแบบทดสอบ ไม่ต้องสมัครสมาชิก",
        tagline="ฮิรางานะ · คาตากานะ ฟรี", icon="あ", accent="#db2777",
        keywords=("ฮิรางานะ", "คาตากานะ", "อักษรภาษาญี่ปุ่น", "ตารางฮิรางานะ"),
    ),
    Microsite(
        key="kanji", domain="คันจิ.online", kind="tool", name="RYU KANJI",
        title="คลังคันจิ N5–N1 คำอ่าน ความหมาย ลำดับขีด คำศัพท์ตัวอย่าง | RYU KANJI",
        description="ค้นหาคันจิ JLPT N5 ถึง N1 พร้อมคำอ่านอง/คุง คำอ่านภาษาไทย ความหมาย ลำดับขีด คำศัพท์ตัวอย่าง และแบบฝึกหัด ฟรี ไม่ต้องสมัครสมาชิก",
        tagline="คลังคันจิ N5 → N1 ฟรี", icon="漢", accent="#7c3aed",
        keywords=("คันจิ", "คันจิ N5", "คันจิ N4", "คันจิ N3", "เรียนคันจิ"),
    ),
    Microsite(
        key="dictionary", domain="พจนานุกรมภาษาญี่ปุ่น.online", kind="tool", name="RYU DICTIONARY",
        title="พจนานุกรมภาษาญี่ปุ่น–ไทย พร้อม AI ช่วยอธิบาย | RYU DICTIONARY",
        description="พจนานุกรมญี่ปุ่น–ไทย และไทย–ญี่ปุ่น มีฟุริงานะ คำอ่านภาษาไทย ประเภทคำ ตัวอย่างประโยค และเสียงอ่าน พร้อม AI ช่วยอธิบาย ใช้ฟรี",
        tagline="พจนานุกรมญี่ปุ่น ⇄ ไทย + AI", icon="book", accent="#0d9488",
        keywords=("พจนานุกรมภาษาญี่ปุ่น", "ดิกชันนารีญี่ปุ่น", "ศัพท์ญี่ปุ่น", "แปลศัพท์ญี่ปุ่น"),
    ),
    Microsite(
        key="translator", domain="แปลภาษาญี่ปุ่น.online", kind="tool", name="RYU TRANSLATOR",
        title="แปลภาษาญี่ปุ่น ⇄ ไทย ด้วย AI เลือกระดับความสุภาพได้ | RYU TRANSLATOR",
        description="แปลภาษาไทยเป็นญี่ปุ่น และญี่ปุ่นเป็นไทย ด้วย AI เลือกภาษาทั่วไป สุภาพ หรือธุรกิจ พร้อมอธิบายสำนวนและเสียงอ่าน ใช้ฟรี",
        tagline="ล่าม AI ไทย ⇄ ญี่ปุ่น", icon="languages", accent="#0284c7",
        keywords=("แปลภาษาญี่ปุ่น", "แปลไทยเป็นญี่ปุ่น", "แปลญี่ปุ่นเป็นไทย", "ล่ามภาษาญี่ปุ่น"),
    ),
    Microsite(
        key="jlpt", domain="วัดระดับภาษาญี่ปุ่น.online", kind="tool", name="RYU JLPT TEST",
        title="แบบทดสอบวัดระดับภาษาญี่ปุ่น ข้อสอบจำลอง JLPT N5–N1 | RYU JLPT TEST",
        description="วัดระดับภาษาญี่ปุ่นฟรี ข้อสอบจำลองแนว JLPT N5 ถึง N1 แยกคำศัพท์ คันจิ ไวยากรณ์ การอ่าน จับเวลา วิเคราะห์คะแนน พร้อมเฉลย (ข้อสอบจำลองของ RYU CLASS ไม่ใช่ข้อสอบทางการ)",
        tagline="ข้อสอบจำลอง JLPT N5 → N1", icon="clipboard", accent="#16a34a",
        keywords=("วัดระดับภาษาญี่ปุ่น", "ข้อสอบ JLPT", "แบบทดสอบภาษาญี่ปุ่น", "ข้อสอบจำลอง N5"),
    ),
)

BY_KEY = {s.key: s for s in SITES}
BY_HOST = {}
for _s in SITES:
    if _s.mount:        # served by its host site, which owns the Host header
        continue
    BY_HOST[_s.host] = _s
    BY_HOST["www." + _s.host] = _s


def all_hosts():
    """Every Host header we answer for (apex + www), for ALLOWED_HOSTS."""
    return list(BY_HOST)


def lookup(host):
    """Map a raw Host header (any case, optional port, unicode or punycode) to a Microsite or None."""
    host = (host or "").split(":", 1)[0].strip().lower().rstrip(".")
    if not host:
        return None
    site = BY_HOST.get(host)
    if site is None and not host.isascii():
        try:
            site = BY_HOST.get(host.encode("idna").decode("ascii"))
        except UnicodeError:
            return None
    return site
