"""Common utilities, mixins, dashboard landing logic."""
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


def portal_redirect(user):
    """Send each role to its own dashboard section."""
    role = getattr(user, "role", None)
    if role in {"super_admin", "business_owner"}:
        return reverse("analytics:business_dashboard")
    if role == "office_staff":
        return reverse("analytics:office_dashboard")
    if role == "project_manager":
        return reverse("analytics:pm_dashboard")
    if role == "worker":
        return reverse("analytics:worker_dashboard")
    if role == "customer":
        return reverse("analytics:customer_dashboard")
    return reverse("analytics:business_dashboard")


@login_required
def dashboard_home(request):
    """Router that sends users to their portal dashboard."""
    return redirect(portal_redirect(request.user))


def public_landing(request):
    """Public marketing page; shows login CTA."""
    return render(request, "common/landing.html")


# ---------- Custom error handlers ----------

def handler404(request, exception=None):
    """Custom 404 page."""
    return render(request, "404.html", status=404)


def handler500(request):
    """Custom 500 page."""
    return render(request, "500.html", status=500)


def handler403(request, exception=None):
    """Custom 403 page."""
    return render(request, "403.html", status=403)


def handler400(request, exception=None):
    """Custom 400 page."""
    return render(request, "400.html", status=400)
