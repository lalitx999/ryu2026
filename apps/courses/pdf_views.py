"""Lesson handouts.  The legacy site served /storage/protected_pdfs/* to anyone holding the link;
here a file is only returned to staff, to anyone for free lessons, or to students entitled to that course level."""
import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache

from core.http import is_admin_user
from courses.models import Lesson
from courses.services.access_service import AccessService


@never_cache
def lesson_pdf(request, filename):
    name = os.path.basename(filename)             # no path components, ever
    if not name.lower().endswith(".pdf"):
        raise Http404
    lessons = list(Lesson.objects.filter(pdf_file__endswith=name, is_active=True)
                   .select_related("course").only("id", "is_free", "course__level"))
    if not lessons:
        raise Http404
    user = request.user
    staff = user.is_authenticated and is_admin_user(user)
    rank = AccessService.user_video_rank(user.id) if user.is_authenticated and not staff else 0
    # one file may back several lessons (legacy data): any lesson that grants access is enough
    allowed = staff or any(l.is_free or rank >= AccessService.LEVEL_RANK.get(l.course.level, 99) > 0 for l in lessons)
    if not allowed:
        raise Http404                              # same answer as "missing": do not reveal which files exist
    for root in (settings.PDF_STORAGE_DIR, os.path.join(settings.BASE_DIR, "storage", "protected_pdfs"),
                 os.path.join(settings.MEDIA_ROOT, "pdfs")):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            resp = FileResponse(open(path, "rb"), content_type="application/pdf")
            resp["Content-Disposition"] = f'inline; filename="{name}"'
            resp["X-Content-Type-Options"] = "nosniff"
            return resp
    raise Http404
