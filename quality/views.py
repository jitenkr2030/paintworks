"""Quality views."""
from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.mixins import internal_required
from crm.models import Customer
from projects.models import Project
from .models import QualityChecklist, Warranty, Complaint, MaintenanceReminder


@admin.register(QualityChecklist)
class QualityChecklistAdmin(admin.ModelAdmin):
    list_display = ("project", "overall_rating", "checked_by", "checked_at")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("subject", "customer", "status", "priority", "created_at")


class QCForm(forms.ModelForm):
    class Meta:
        model = QualityChecklist
        fields = ("project", "surface_preparation_ok", "paint_shade_approved",
                  "finish_quality_ok", "material_quality_verified",
                  "cleanup_done", "customer_inspection_done",
                  "overall_rating", "notes")


class WarrantyForm(forms.ModelForm):
    class Meta:
        model = Warranty
        fields = ("project", "warranty_period_months", "start_date",
                  "end_date", "coverage", "terms", "is_active")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("customer", "project", "subject", "description",
                  "status", "priority", "assigned_to", "resolution")
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "resolution": forms.Textarea(attrs={"rows": 3})}


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceReminder
        fields = ("customer", "project", "service_type", "next_due_date",
                  "interval_months", "is_active", "notes")
        widgets = {"next_due_date": forms.DateInput(attrs={"type": "date"})}


@internal_required
def qc_list(request):
    qs = QualityChecklist.objects.all().order_by("-checked_at")
    return render(request, "quality/qc_list.html", {"items": qs})


@internal_required
def qc_create(request):
    form = QCForm(request.POST or None)
    if form.is_valid():
        qc = form.save(commit=False)
        qc.checked_by = request.user
        qc.save()
        return redirect(reverse("quality:qc_list"))
    return render(request, "quality/qc_form.html", {"form": form, "title": "Quality Check"})


@internal_required
def warranty_list(request):
    qs = Warranty.objects.all().order_by("-start_date")
    return render(request, "quality/warranty_list.html", {"items": qs})


@internal_required
def warranty_create(request):
    form = WarrantyForm(request.POST or None)
    if form.is_valid():
        w = form.save(commit=False)
        if not w.end_date:
            from datetime import timedelta
            w.end_date = w.start_date + timedelta(days=30 * w.warranty_period_months)
        w.save()
        return redirect(reverse("quality:warranty_list"))
    return render(request, "quality/warranty_form.html",
                  {"form": form, "title": "Add Warranty"})


@internal_required
def complaint_list(request):
    qs = Complaint.objects.all().order_by("-created_at")
    return render(request, "quality/complaint_list.html", {"items": qs})


@internal_required
def complaint_create(request):
    form = ComplaintForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(reverse("quality:complaint_list"))
    return render(request, "quality/complaint_form.html",
                  {"form": form, "title": "Log Complaint"})


@internal_required
def complaint_resolve(request, pk):
    c = get_object_or_404(Complaint, pk=pk)
    if request.method == "POST":
        c.resolution = request.POST.get("resolution", "")
        c.status = "resolved"
        c.resolved_at = timezone.now()
        c.save()
    return redirect(reverse("quality:complaint_list"))


@internal_required
def maintenance_list(request):
    qs = MaintenanceReminder.objects.filter(is_active=True).order_by("next_due_date")
    return render(request, "quality/maintenance_list.html", {"items": qs})


@internal_required
def maintenance_create(request):
    form = MaintenanceForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(reverse("quality:maintenance_list"))
    return render(request, "quality/maintenance_form.html",
                  {"form": form, "title": "Schedule Maintenance"})
