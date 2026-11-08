from django.contrib.auth import login, logout, update_session_auth_hash

from core.http import ajax_view, json_body, ok
from users.selectors.user_selector import profile_payload
from users.services import auth_service


@ajax_view("POST")
def login_view(request):
    data = json_body(request)
    user = auth_service.login_user(data.get("email"), data.get("password"))
    login(request, user, backend="users.backends.EmailBackend")
    return ok(profile_payload(user), message="เข้าสู่ระบบสำเร็จ!")


@ajax_view("POST")
def logout_view(request):
    logout(request)
    return ok(message="ออกจากระบบแล้ว")


@ajax_view("POST")
def register_view(request):
    user = auth_service.register_student(request.POST, request.FILES.get("slip"))
    return ok({"email": user.email}, status=201, verification_required=True,
              message="ลงทะเบียนเรียบร้อยแล้ว กรุณาตรวจสอบอีเมลและกรอกรหัส 6 หลักเพื่อยืนยันบัญชี")


@ajax_view("POST")
def verify_email_view(request):
    data = json_body(request)
    user = auth_service.verify_email(data.get("email"), data.get("code"))
    login(request, user, backend="users.backends.EmailBackend")
    return ok(profile_payload(user), message="ยืนยันอีเมลเรียบร้อยแล้ว")


@ajax_view("POST")
def resend_verification_view(request):
    auth_service.resend_verification(json_body(request).get("email"))
    return ok(message="หากอีเมลนี้รอการยืนยัน ระบบจะส่งรหัสใหม่ให้")


@ajax_view("POST")
def reset_password_view(request):
    data = json_body(request)
    auth_service.reset_password(data.get("email"), data.get("phone"), data.get("new_password"))
    return ok(message="ตั้งรหัสผ่านใหม่สำเร็จ สามารถเข้าสู่ระบบด้วยรหัสผ่านใหม่ได้ทันที!")


@ajax_view("GET", "POST", login=True)
def profile_view(request):
    if request.method == "POST":
        auth_service.update_profile(request.user, json_body(request))
        update_session_auth_hash(request, request.user)  # keep the session alive after a password change
        return ok(profile_payload(request.user), message="บันทึกข้อมูลส่วนตัวเรียบร้อยแล้วค่ะ")
    return ok(profile_payload(request.user))
