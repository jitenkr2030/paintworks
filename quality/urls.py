"""Quality URLs."""
from django.urls import path
from . import views

app_name = "quality"

urlpatterns = [
    path("checks/", views.qc_list, name="qc_list"),
    path("checks/new/", views.qc_create, name="qc_create"),
    path("warranties/", views.warranty_list, name="warranty_list"),
    path("warranties/new/", views.warranty_create, name="warranty_create"),
    path("complaints/", views.complaint_list, name="complaint_list"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
    path("complaints/<int:pk>/resolve/", views.complaint_resolve, name="complaint_resolve"),
    path("maintenance/", views.maintenance_list, name="maintenance_list"),
    path("maintenance/new/", views.maintenance_create, name="maintenance_create"),
]
