"""Mixins and decorators shared across apps."""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse


def internal_required(view_func):
    """Only allow internal company roles (owner/staff/pm/worker/super_admin)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(reverse("accounts:login") + f"?next={request.path}")
        if not getattr(user, "is_internal", False):
            return redirect(reverse("dashboard"))
        return view_func(request, *args, **kwargs)
    return _wrapped


def management_required(view_func):
    """Only allow management roles (super_admin/owner/office_staff)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(reverse("accounts:login") + f"?next={request.path}")
        if not getattr(user, "is_management", False):
            return redirect(reverse("dashboard"))
        return view_func(request, *args, **kwargs)
    return _wrapped
