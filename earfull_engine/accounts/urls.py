# earfull_engine/urls.py

from django.contrib import admin
from django.urls import path
from views import MeView, RegisterUser

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT auth
    path("api/auth/register/", RegisterUser.as_view()),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="jwt_login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("api/auth/me/", MeView.as_view(), name="MeView")
]
