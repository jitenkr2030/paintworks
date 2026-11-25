"""Analytics URLs."""
from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("business/", views.business_dashboard, name="business_dashboard"),
    path("office/", views.office_dashboard, name="office_dashboard"),
    path("pm/", views.pm_dashboard, name="pm_dashboard"),
    path("worker/", views.worker_dashboard, name="worker_dashboard"),
    path("customer/", views.customer_dashboard, name="customer_dashboard"),
    path("reports/sales/", views.sales_report, name="sales_report"),
    path("reports/projects/", views.project_report, name="project_report"),
    path("reports/customers/", views.customer_report, name="customer_report"),
    path("reports/workers/", views.worker_report, name="worker_report"),
    path("reports/materials/", views.material_report, name="material_report"),
    path("reports/quotations/", views.quotation_report, name="quotation_report"),
    path("reports/financial/", views.financial_report, name="financial_report"),
    path("reports/services/", views.service_report, name="service_report"),
    # V3: Advanced BI
    path("kpi/", views.kpi_dashboard, name="kpi_dashboard"),
    path("trends/", views.trends_forecast, name="trends_forecast"),
    path("service-popularity/", views.service_popularity, name="service_popularity"),
    path("photo-progress/<int:project_pk>/", views.photo_progress, name="photo_progress"),
]
