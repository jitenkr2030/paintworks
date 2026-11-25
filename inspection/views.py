"""Inspection admin and views."""
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from booking.models import Booking
from .models import SiteInspection, RoomMeasurement, InspectionPhoto
from django.forms import inlineformset_factory


@admin.register(SiteInspection)
class SiteInspectionAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "inspector", "status", "scheduled_at")
    list_filter = ("status",)


@admin.register(RoomMeasurement)
class RoomMeasurementAdmin(admin.ModelAdmin):
    list_display = ("room_name", "inspection", "length", "width", "height")


class SiteInspectionForm(forms.ModelForm):
    class Meta:
        model = SiteInspection
        fields = ("booking", "inspector", "scheduled_at", "status",
                  "overall_condition", "recommendations", "customer_approved")
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "overall_condition": forms.Textarea(attrs={"rows": 3}),
            "recommendations": forms.Textarea(attrs={"rows": 3}),
        }


RoomMeasurementFormSet = inlineformset_factory(
    SiteInspection, RoomMeasurement,
    fields=("room_name", "length", "width", "height",
            "door_width", "door_height", "door_count",
            "window_width", "window_height", "window_count",
            "ceiling_area", "surface_condition",
            "dampness_observed", "cracks_observed", "notes"),
    extra=3, can_delete=True,
)


@internal_required
def inspection_list(request):
    inspections = SiteInspection.objects.all().select_related("booking", "inspector").order_by("-created_at")
    if request.GET.get("export") == "xlsx":
        cols = [
            ("ID", "id"),
            ("Booking ID", lambda i: i.booking.id if i.booking else ""),
            ("Inspector", lambda i: i.inspector.display_name if i.inspector else ""),
            ("Scheduled At", "scheduled_at"),
            ("Status", "status"),
            ("Rooms Count", lambda i: i.room_measurements.count()),
        ]
        return export_queryset_to_excel(inspections, cols, "inspections", "Inspections")
    page = paginate(inspections, request, per_page=20)
    return render(request, "inspection/list.html",
                  {"inspections": page.object_list, "page_obj": page})


@internal_required
def inspection_detail(request, pk):
    inspection = get_object_or_404(SiteInspection, pk=pk)
    return render(request, "inspection/detail.html", {"inspection": inspection})


@internal_required
def inspection_create(request):
    form = SiteInspectionForm(request.POST or None)
    formset = RoomMeasurementFormSet(request.POST or None)
    if form.is_valid() and formset.is_valid():
        inspection = form.save()
        formset.instance = inspection
        formset.save()
        for f in request.FILES.getlist("photos"):
            InspectionPhoto.objects.create(inspection=inspection, image=f)
        return redirect(reverse("inspection:detail", args=[inspection.pk]))
    return render(request, "inspection/form.html",
                  {"form": form, "formset": formset, "title": "Schedule Inspection"})


@internal_required
def inspection_edit(request, pk):
    inspection = get_object_or_404(SiteInspection, pk=pk)
    form = SiteInspectionForm(request.POST or None, instance=inspection)
    formset = RoomMeasurementFormSet(request.POST or None, instance=inspection)
    if form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        for f in request.FILES.getlist("photos"):
            InspectionPhoto.objects.create(inspection=inspection, image=f)
        return redirect(reverse("inspection:detail", args=[inspection.pk]))
    return render(request, "inspection/form.html",
                  {"form": form, "formset": formset,
                   "title": f"Edit Inspection #{inspection.pk}",
                   "inspection": inspection})


@internal_required
def measurement_report(request, pk):
    """Customer-approved measurement report view."""
    inspection = get_object_or_404(SiteInspection, pk=pk)
    rooms = inspection.room_measurements.all()
    totals = {
        "wall": sum(r.wall_area for r in rooms),
        "ceiling": sum(r.total_ceiling_area for r in rooms),
        "openings": sum(r.openings_area for r in rooms),
        "net": sum(r.net_paint_area for r in rooms),
    }
    return render(request, "inspection/measurement_report.html",
                  {"inspection": inspection, "rooms": rooms, "totals": totals})
