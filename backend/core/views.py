from django.db import connections
from django.http import JsonResponse


def health_check(request):
    db_ok = False
    try:
        connections["default"].cursor()
        db_ok = True
    except Exception:
        pass

    return JsonResponse({
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    })
