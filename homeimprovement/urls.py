"""Root URL configuration for the platform."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from common.views import dashboard_home, public_landing

handler404 = "common.views.handler404"
handler500 = "common.views.handler500"
handler403 = "common.views.handler403"
handler400 = "common.views.handler400"

urlpatterns = [
    path("", public_landing, name="public_landing"),
    path("admin/", admin.site.urls),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("dashboard/", dashboard_home, name="dashboard"),
    path("services/", include(("services.urls", "services"), namespace="services")),
    path("crm/", include(("crm.urls", "crm"), namespace="crm")),
    path("booking/", include(("booking.urls", "booking"), namespace="booking")),
    path("inspection/", include(("inspection.urls", "inspection"), namespace="inspection")),
    path("estimation/", include(("estimation.urls", "estimation"), namespace="estimation")),
    path("projects/", include(("projects.urls", "projects"), namespace="projects")),
    path("workforce/", include(("workforce.urls", "workforce"), namespace="workforce")),
    path("inventory/", include(("inventory.urls", "inventory"), namespace="inventory")),
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),
    path("analytics/", include(("analytics.urls", "analytics"), namespace="analytics")),
    path("quality/", include(("quality.urls", "quality"), namespace="quality")),
    # V2/V3 apps
    path("notifications/", include(("notifications.urls", "notifications"), namespace="notifications")),
    path("ai/", include(("aiassistant.urls", "aiassistant"), namespace="aiassistant")),
    path("subscriptions/", include(("subscriptions.urls", "subscriptions"), namespace="subscriptions")),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.svg", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
