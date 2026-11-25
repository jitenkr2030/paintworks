"""Context processor exposing portal/role info to all templates."""
from django.conf import settings


def portal_context(request):
    user = getattr(request, "user", None)
    role = None
    is_internal = False
    is_management = False
    if user and user.is_authenticated:
        role = user.role
        is_internal = getattr(user, "is_internal", False)
        is_management = getattr(user, "is_management", False)
    return {
        "PLATFORM_NAME": "PaintWorks",
        "PLATFORM_TAGLINE": "Whitewash, Painting & Home Improvement Management",
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "₹"),
        "current_role": role,
        "is_internal": is_internal,
        "is_management": is_management,
    }
