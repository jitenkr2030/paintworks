"""Inventory URLs."""
from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/new/", views.supplier_create, name="supplier_create"),
    path("materials/", views.material_list, name="material_list"),
    path("materials/new/", views.material_create, name="material_create"),
    path("materials/<int:pk>/edit/", views.material_edit, name="material_edit"),
    path("po/", views.po_list, name="po_list"),
    path("po/new/", views.po_create, name="po_create"),
    path("po/<int:pk>/", views.po_detail, name="po_detail"),
    path("po/<int:pk>/lines/new/", views.po_add_line, name="po_add_line"),
    path("issues/", views.material_issue_list, name="material_issue_list"),
    path("issues/new/", views.material_issue_create, name="material_issue_create"),
    path("returns/", views.material_return_list, name="material_return_list"),
    path("returns/new/", views.material_return_create, name="material_return_create"),
]
