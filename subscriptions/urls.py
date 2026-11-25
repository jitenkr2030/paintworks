"""Subscriptions URLs."""
from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/new/", views.plan_create, name="plan_create"),
    path("plans/<int:pk>/edit/", views.plan_edit, name="plan_edit"),
    path("", views.subscription_list, name="subscription_list"),
    path("new/", views.subscription_create, name="subscription_create"),
    path("<int:pk>/", views.subscription_detail, name="subscription_detail"),
    path("<int:pk>/cancel/", views.subscription_cancel, name="subscription_cancel"),
    path("<int:sub_pk>/invoices/new/", views.subscription_invoice_create,
          name="invoice_create"),
    path("<int:sub_pk>/invoices/<int:inv_pk>/pay/",
          views.subscription_invoice_mark_paid, name="invoice_mark_paid"),
    path("usage/", views.usage_report, name="usage_report"),
]
