"""Workforce URLs."""
from django.urls import path
from . import views
from .payroll_views import (
    payroll_cycle_list, payroll_cycle_create, payroll_cycle_detail,
    payroll_entry_edit, payroll_process_payment,
    contractor_settlement_list, contractor_settlement_create,
    contractor_settlement_mark_paid,
)

app_name = "workforce"

urlpatterns = [
    path("", views.worker_list, name="list"),
    path("new/", views.worker_create, name="create"),
    path("<int:pk>/", views.worker_detail, name="detail"),
    path("<int:pk>/edit/", views.worker_edit, name="edit"),
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/new/", views.attendance_create, name="attendance_create"),
    path("assignments/", views.assignment_list, name="assignment_list"),
    path("assignments/new/", views.assignment_create, name="assignment_create"),
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/new/", views.payment_create, name="payment_create"),
    # V2: Payroll & contractor settlements
    path("payroll/", payroll_cycle_list, name="payroll_cycle_list"),
    path("payroll/new/", payroll_cycle_create, name="payroll_cycle_create"),
    path("payroll/<int:pk>/", payroll_cycle_detail, name="payroll_cycle_detail"),
    path("payroll/<int:cycle_pk>/entries/<int:entry_pk>/edit/",
         payroll_entry_edit, name="payroll_entry_edit"),
    path("payroll/<int:cycle_pk>/entries/<int:entry_pk>/pay/",
         payroll_process_payment, name="payroll_process_payment"),
    path("contractor-settlements/", contractor_settlement_list,
         name="contractor_settlement_list"),
    path("contractor-settlements/new/", contractor_settlement_create,
         name="contractor_settlement_create"),
    path("contractor-settlements/<int:pk>/pay/",
         contractor_settlement_mark_paid, name="contractor_settlement_pay"),
]
