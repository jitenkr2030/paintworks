"""CRM URLs."""
from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/<int:customer_pk>/properties/new/", views.property_create, name="property_create"),
    path("leads/", views.lead_list, name="lead_list"),
    path("leads/new/", views.lead_create, name="lead_create"),
    path("leads/<int:pk>/edit/", views.lead_edit, name="lead_edit"),
    path("followups/new/", views.followup_create, name="followup_create"),
]
