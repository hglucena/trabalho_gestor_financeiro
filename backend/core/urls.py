from django.contrib import admin
from django.urls import path

from core.views import health_check, LoginView, MeView, RegistroView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/registro/", RegistroView.as_view(), name="registro"),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/me/", MeView.as_view(), name="me"),
]
