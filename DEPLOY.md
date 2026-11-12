# คู่มือวันปล่อยจริง (ย้ายจาก homeserver + Vercel มาที่ VPS)

เว็บจริงสุดท้าย: **https://www.ryusosense.online** · VPS: `72.60.199.62` · ผู้ใช้ล็อกอิน: `ryuadmin` (กุญแจ SSH เท่านั้น)
ที่ซ้อมแล้วผ่าน: ข้อมูลเดิม, ล็อกอินบัญชีเก่า, วิดีโอ/PDF/สลิป, Telegram, อีเมล, สมัคร+แจ้งชำระเงิน, HTTPS (`new.ryusosense.online`), systemd, สำรองข้อมูลทุกคืน, ล็อก SSH

> ทำทีละบล็อก อ่านผลก่อนไปบล็อกถัดไป ห้ามวางคีย์/รหัสผ่านในแชท

## 0) เตรียมก่อนวันจริง (ทำล่วงหน้าได้ ไม่กระทบใคร)
**0.1 ให้ homeserver ส่งไฟล์เข้า VPS ด้วยกุญแจ** (เพราะปิดล็อกอิน root/รหัสผ่านแล้ว)
- homeserver: `[ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -t ed25519 -C homeserver-to-vps; cat ~/.ssh/id_ed25519.pub`
- VPS (ryuadmin): `echo 'ssh-ed25519 AAAA...ที่ได้...' | sudo tee -a /home/ryuadmin/.ssh/authorized_keys`
- ทดสอบจาก homeserver: `ssh ryuadmin@72.60.199.62 "echo ok"` (ต้องไม่ถามรหัสผ่านของ VPS)

**0.2 ตัดสินใจ `MERCHANT_ACCOUNT_NUMBER`** (เลขบัญชีรับเงินของร้าน) ว่าง = ไม่เช็คบัญชีผู้รับ (เหมือนเว็บเดิม) · ใส่ = สลิปที่โอนเข้าบัญชีอื่นจะไม่ผ่านอัตโนมัติ (แนะนำใส่ แล้วทดสอบกับสลิปจริง 1 ใบหลังปล่อย)

## 1) หยุดเว็บเก่า แล้ว dump — homeserver (ทำในหน้าต่างเดียวกันต่อเนื่อง)
อ่านรหัสฐานข้อมูลเก็บในตัวแปร **ก่อน** หยุดเว็บ (หยุดแล้ว `docker exec ryuclass_backend` จะอ่านไม่ได้) จากนั้นหยุดเว็บ แล้วค่อย dump:
```bash
PW=$(docker exec ryuclass_backend printenv DB_PASS)
docker stop ryuclass_backend
docker exec -e MYSQL_PWD="$PW" shared-mariadb mariadb-dump -h shared-mariadb -uroot --single-transaction --routines --default-character-set=utf8mb4 ryuclass_db | gzip > ~/ryu_final.sql.gz
gunzip -t ~/ryu_final.sql.gz && ls -lh ~/ryu_final.sql.gz && zcat ~/ryu_final.sql.gz | grep -c '^CREATE TABLE'   # ต้องได้ 46
```

## 2) ส่งข้อมูลล่าสุดไป VPS — homeserver
ส่งไฟล์ dump (ตรวจ checksum ทั้งสองฝั่ง):
```bash
rsync -avzP ~/ryu_final.sql.gz ryuadmin@72.60.199.62:~/ryu_import/
sha256sum ~/ryu_final.sql.gz && ssh ryuadmin@72.60.199.62 'sha256sum ~/ryu_import/ryu_final.sql.gz'
# สลิป (ที่ใช้งานจริงตอนนี้ + คลังเก่า) และ PDF — ส่งเฉพาะไฟล์ที่เพิ่ม
rsync -avzP ~/Webservice/ryuclassV2/storage/slips/ ryuadmin@72.60.199.62:~/ryu_import/slips/
rsync -avzP /mnt/hdd_backup/storage/php_app/uploads/slips/ ryuadmin@72.60.199.62:~/ryu_import/slips/
rsync -avzP /mnt/hdd_backup/storage/php_app/uploads/protected_pdfs/ ryuadmin@72.60.199.62:~/ryu_import/protected_pdfs/
ls ~/Webservice/ryuclassV2/storage/   # ถ้ามี protected_pdfs ใหม่ในนี้ ให้ rsync เพิ่มด้วย
```

## 3) นำเข้าบน VPS (ryuadmin)
**3.1 หยุดแอป + แปลง collation (MariaDB → MySQL) + สร้างฐานข้อมูลใหม่สะอาด**
```bash
sudo systemctl stop ryu-web ryu-worker
zcat ~/ryu_import/ryu_final.sql.gz | sed -E 's/utf8mb4_uca1400_[a-z_]+/utf8mb4_unicode_ci/g' > ~/ryu_import/ryu_for_mysql.sql
grep -c uca1400 ~/ryu_import/ryu_for_mysql.sql      # ต้องได้ 0
sudo mysql -e "DROP DATABASE IF EXISTS ryuclass_db; CREATE DATABASE ryuclass_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON ryuclass_db.* TO 'ryu'@'localhost'; FLUSH PRIVILEGES;"
sudo mysql --default-character-set=utf8mb4 ryuclass_db < ~/ryu_import/ryu_for_mysql.sql && echo "นำเข้าเสร็จ"
sudo mysql ryuclass_db -e "SELECT COUNT(*) users FROM users; SELECT COUNT(*) payments FROM payments; SELECT COUNT(*) enrollments FROM enrollments;"   # เทียบกับตัวเลขจาก homeserver
```
**3.2 ปรับประวัติ migration ให้ตรง repo** (ฐานข้อมูลเดิมดูแลด้วย Django รุ่นก่อน)
```bash
sudo mysql ryuclass_db -e "INSERT INTO django_migrations (app, name, applied) VALUES ('courses','0003_ryutube',NOW(6)), ('courses','0006_remove_ryutubevideo_category_and_more',NOW(6));"
cd /srv/ryu2026
P="sudo -u ryu env DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py"
$P migrate courses 0009 --fake 2>&1 | tail -4
$P migrate --fake-initial 2>&1 | tail -6
$P adopt_legacy_db --force 2>&1 | head -6      # ต้องเห็น "สร้างตารางใหม่ 0" และ "เพิ่มคอลัมน์: -" (ห้ามใส่ --apply)
```
> ถ้า 3.2 ขึ้นข้อความที่ไม่ตรงนี้ **หยุดแล้วถามก่อน** เพราะ django_migrations ของเว็บเดิมอาจต่างจากที่ซ้อม (ดูสถานะด้วย `$P showmigrations courses`)

**3.3 ไฟล์ + ตั้งค่า**
```bash
sudo rsync -a ~/ryu_import/slips/ /srv/ryu2026/storage/slips/
sudo rsync -a ~/ryu_import/protected_pdfs/ /srv/ryu2026/storage/protected_pdfs/
sudo chown -R ryu:ryu /srv/ryu2026/storage
sudo sed -i 's/^DB_NAME=.*/DB_NAME=ryuclass_db/' /srv/ryu2026/.env
sudo sed -i 's/^DB=.*/DB=ryuclass_db/' /usr/local/bin/ryu-backup.sh
```
ตรวจ `sudo grep -E '^(DB_NAME|DB_USER)=' /srv/ryu2026/.env` แล้วเริ่มแอป: `sudo systemctl start ryu-web ryu-worker`
ทดสอบที่ `https://new.ryusosense.online`: ล็อกอินบัญชีเก่า, เปิดสลิปเก่าในแอดมิน, เปิดคอร์ส/PDF

## 4) เปลี่ยนโดเมนจริง
**4.1 Cloudflare DNS** (DNS only / เมฆเทา · ห้ามแตะเรคคอร์ด MX, SPF, DKIM, DMARC, autoconfig/autodiscover)
- `ryusosense.online` (A) แก้จาก `76.76.21.21` เป็น `72.60.199.62`
- `www` (CNAME → cname.vercel-dns.com) ลบ แล้วสร้าง A ชื่อ `www` → `72.60.199.62`
- รอให้ `getent hosts www.ryusosense.online` บน VPS ขึ้น `72.60.199.62`

**4.2 nginx + HTTPS ทั้งสองชื่อ**
```bash
sudo sed -i 's/server_name new.ryusosense.online;/server_name www.ryusosense.online new.ryusosense.online;/' /etc/nginx/sites-available/ryu
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d www.ryusosense.online -d new.ryusosense.online --expand --redirect
sudo tee /etc/nginx/sites-available/ryu-apex >/dev/null <<'EOF'
server {
    listen 80;
    server_name ryusosense.online;
    return 301 https://www.ryusosense.online$request_uri;
}
EOF
sudo ln -sf /etc/nginx/sites-available/ryu-apex /etc/nginx/sites-enabled/ryu-apex && sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d ryusosense.online --redirect
```
**4.3 บอกแอปว่าโดเมนจริงคืออะไร** (แล้วรีสตาร์ต)
```bash
sudo sed -i -E 's|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=www.ryusosense.online,ryusosense.online,new.ryusosense.online,localhost,127.0.0.1|; s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://www.ryusosense.online,https://ryusosense.online,https://new.ryusosense.online|; s|^SITE_URL=.*|SITE_URL=https://www.ryusosense.online|' /srv/ryu2026/.env
sudo systemctl restart ryu-web ryu-worker
```
**4.4 เปิดตัวส่งอีเมลเตือนต่ออายุ (เปิดตอนปล่อยจริงเท่านั้น)**: `sudo systemctl enable --now ryu-beat`

## 5) ตรวจหลังปล่อย
- `https://www.ryusosense.online` เปิดได้, `https://ryusosense.online` เด้งไป `www`, `http://` เด้งไป `https://`
- ล็อกอินบัญชีนักเรียนเก่า + แอดมิน, เล่นวิดีโอ, เปิด PDF, ดูสลิปเก่า
- Telegram แอดมินเด้งเมื่อมีสลิปใหม่ (ให้นักเรียนจริง/บัญชีทดสอบลอง 1 ครั้ง)
- `sudo systemctl is-active ryu-web ryu-worker ryu-beat nginx mysql redis-server`
- วันถัดไป: `sudo tail -3 /var/log/ryu-backup.log` (ต้องเห็น `backup ok` ของตี 3:30)
- สุดท้าย (ไม่เร่ง): ถอดโดเมนออกจากโปรเจกต์ Vercel `ryuclassv2` และเก็บ homeserver เดิมไว้ไม่แตะอีกหลายวัน

## ถอยกลับ (ถ้าเกิดเรื่อง)
1. Cloudflare: `ryusosense.online` A → `76.76.21.21`, ลบ A ของ `www` แล้วสร้าง CNAME `www` → `cname.vercel-dns.com`
2. homeserver: `docker start ryuclass_backend`
> ข้อมูลที่เกิดบน VPS หลังปล่อยจะไม่ย้อนกลับไปเว็บเก่าเอง ถ้าต้องถอยหลังมีคนใช้ไปแล้ว ให้ dump จาก VPS ก่อน (`sudo /usr/local/bin/ryu-backup.sh`)
