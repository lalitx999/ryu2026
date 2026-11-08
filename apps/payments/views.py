import os

from django.conf import settings
from django.http import FileResponse, Http404

from core.http import ajax_view, ok
from payments.models import Payment
from payments.services import payment_service


@ajax_view("POST", login=True)
def upload_slip(request):
    payment = payment_service.upload_slip_existing_user(request.user, request.POST, request.FILES.get("slip"))
    return ok({"payment_id": payment.id, "status": payment.status}, status=201,
              message="อัปโหลดสลิปเรียบร้อยแล้ว กรุณารอแอดมินตรวจสอบสลิปภายใน 24 ชม.")


@ajax_view("GET", login=True)
def slip_image(request, payment_id):
    """Slips are private: only the owner or an admin may fetch them (the old setup served them publicly)."""
    from core.http import is_admin_user

    payment = Payment.objects.filter(pk=payment_id).only("user_id", "slip_path").first()
    if not payment or not payment.slip_path or not (is_admin_user(request.user) or payment.user_id == request.user.id):
        raise Http404
    path = os.path.join(settings.SLIPS_STORAGE_DIR, os.path.basename(payment.slip_path))
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, "rb"))
