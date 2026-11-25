"""Inspection URLs."""
from django.urls import path
from . import views

app_name = "inspection"

urlpatterns = [
    path("", views.inspection_list, name="list"),
    path("new/", views.inspection_create, name="create"),
    path("<int:pk>/", views.inspection_detail, name="detail"),
    path("<int:pk>/edit/", views.inspection_edit, name="edit"),
    path("<int:pk>/report/", views.measurement_report, name="measurement_report"),
]
