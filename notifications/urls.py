"""Notifications URLs."""
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("templates/", views.template_list, name="template_list"),
    path("templates/new/", views.template_create, name="template_create"),
    path("logs/", views.log_list, name="log_list"),
    path("send/", views.send_notification, name="send"),
]
