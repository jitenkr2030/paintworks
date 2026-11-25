"""Booking URLs."""
from django.urls import path
from . import views

app_name = "booking"

urlpatterns = [
    path("", views.booking_list, name="list"),
    path("new/", views.booking_create, name="create"),
    path("mine/new/", views.customer_booking_create, name="customer_create"),
    path("<int:pk>/", views.booking_detail, name="detail"),
    path("<int:pk>/edit/", views.booking_edit, name="edit"),
    path("<int:pk>/status/", views.booking_status_update, name="status_update"),
]
