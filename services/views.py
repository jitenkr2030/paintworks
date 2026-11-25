"""Services admin and views."""
from django.contrib import admin
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import ServiceCategory, ServiceSubcategory, CoverageRate


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "icon", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(ServiceSubcategory)
class ServiceSubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "code", "default_unit", "default_rate", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "code")


@admin.register(CoverageRate)
class CoverageRateAdmin(admin.ModelAdmin):
    list_display = ("material_name", "unit", "coverage_per_unit", "coats", "is_active")
    list_filter = ("is_active",)


@login_required
def service_catalogue(request):
    cats = ServiceCategory.objects.filter(is_active=True).prefetch_related("subcategories")
    return render(request, "services/catalogue.html", {"categories": cats})
