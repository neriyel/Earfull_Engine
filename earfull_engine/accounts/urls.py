# earfull_engine/urls.py

from django.contrib import admin
from django.urls import path
from . views import MeView, RegisterUser

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT auth
    path("register/", RegisterUser.as_view()),
    path("login/", TokenObtainPairView.as_view(), name="jwt_login"),
    path("refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("me/", MeView.as_view(), name="MeView")
]
