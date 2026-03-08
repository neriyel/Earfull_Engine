from django.urls import path
from . import views

app_name = "spotify"

urlpatterns = [
    # OAuth
    path("connect/", views.spotify_connect, name="spotify_connect"),
    path("callback/", views.spotify_callback, name="spotify_callback"),
    # Sync
    path("sync/recent/", views.sync_recently_played, name="sync_recently_played"),
    # Dashboard
    path("dashboard/summary/", views.dashboard_summary, name="dashboard_summary"),
    path("dashboard/heatmap/", views.dashboard_heatmap, name="dashboard_heatmap"),
    path("dashboard/top/", views.dashboard_top, name="dashboard_top"),
]
