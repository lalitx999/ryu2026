from django.conf import settings

from .http import is_admin_user


def site(request):
    user = request.user
    return {
        "SITE_URL": settings.SITE_URL,
        "IS_ADMIN_USER": user.is_authenticated and is_admin_user(user),
        "LINE_SUPPORT_URL": "https://line.me/R/ti/p/@406khzxf?oat_content=url&ts=09111222",
        "BANK_INFO": {
            "bank": "ธ.กรุงเทพ",
            "name": "บจ. ออนไลน์ ซะโลน (ประเทศไทย)",
            "account": "639-7-16623-9",
        },
    }
