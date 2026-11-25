"""Estimation URLs."""
from django.urls import path
from . import views

app_name = "estimation"

urlpatterns = [
    path("", views.quotation_list, name="list"),
    path("new/", views.quotation_create, name="create"),
    path("<int:pk>/", views.quotation_detail, name="detail"),
    path("<int:pk>/edit/", views.quotation_edit, name="edit"),
    path("<int:pk>/pdf/", views.quotation_pdf, name="pdf"),
    path("<int:pk>/status/", views.quotation_status_update, name="status_update"),
    path("<int:pk>/lines/new/", views.quotation_add_line, name="add_line"),
    path("<int:pk>/lines/<int:line_pk>/delete/", views.quotation_delete_line, name="delete_line"),
    # V2: Advanced estimation
    path("paint-calculator/", views.paint_calculator, name="paint_calculator"),
    path("auto-estimate/<int:inspection_pk>/", views.auto_estimate_from_inspection, name="auto_estimate"),
]
