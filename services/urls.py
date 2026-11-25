"""Services URLs."""
from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.service_catalogue, name="catalogue"),
]
