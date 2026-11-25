"""Billing URLs."""
from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("invoices/<int:pk>/lines/new/", views.invoice_add_line, name="invoice_add_line"),
    path("invoices/<int:pk>/lines/<int:line_pk>/delete/", views.invoice_delete_line, name="invoice_delete_line"),
    path("invoices/<int:pk>/payments/new/", views.invoice_add_payment, name="invoice_add_payment"),
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/new/", views.expense_create, name="expense_create"),
    path("profitability/", views.profitability_report, name="profitability"),
    path("my-invoices/", views.my_invoices, name="my_invoices"),
]
