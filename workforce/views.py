"""Workforce views."""
from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from projects.models import Project
from .models import Worker, WorkerAttendance, WorkerAssignment, WorkerPayment, WorkerLeave


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("name", "worker_type", "phone", "payment_mode", "wage_rate", "is_active")
    list_filter = ("worker_type", "payment_mode", "is_active")


@admin.register(WorkerAttendance)
class WorkerAttendanceAdmin(admin.ModelAdmin):
    list_display = ("worker", "date", "status", "hours_worked", "project")


class WorkerForm(forms.ModelForm):
    class Meta:
        model = Worker
        fields = ("name", "phone", "worker_type", "skills", "payment_mode",
                  "wage_rate", "address", "city", "id_proof", "emergency_contact",
                  "is_active", "rating", "joined_at")
        widgets = {"joined_at": forms.DateInput(attrs={"type": "date"})}


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = WorkerAttendance
        fields = ("worker", "project", "date", "check_in", "check_out",
                  "hours_worked", "status", "notes")
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "check_in": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "check_out": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = WorkerAssignment
        fields = ("worker", "project", "task", "is_active", "notes")


class PaymentForm(forms.ModelForm):
    class Meta:
        model = WorkerPayment
        fields = ("worker", "project", "period_start", "period_end", "amount",
                  "paid_on", "method", "status", "notes")
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "paid_on": forms.DateInput(attrs={"type": "date"}),
        }


@internal_required
def worker_list(request):
    q = request.GET.get("q", "")
    workers = Worker.objects.all().order_by("-created_at")
    if q:
        workers = workers.filter(name__icontains=q) | workers.filter(phone__icontains=q)
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Name", "name"),
            ("Type", "get_worker_type_display"),
            ("Phone", "phone"),
            ("Skills", "skills"),
            ("Payment Mode", "get_payment_mode_display"),
            ("Wage Rate", "wage_rate"),
            ("Rating", "rating"),
            ("Active", "is_active"),
        ]
        return export_queryset_to_excel(workers, cols, "workers", "Workers")
    page = paginate(workers, request, per_page=20)
    return render(request, "workforce/list.html",
                  {"workers": page.object_list, "page_obj": page, "q": q})


@internal_required
def worker_detail(request, pk):
    worker = get_object_or_404(Worker, pk=pk)
    return render(request, "workforce/detail.html", {"worker": worker})


@internal_required
def worker_create(request):
    form = WorkerForm(request.POST or None)
    if form.is_valid():
        worker = form.save(commit=False)
        if request.user.company:
            worker.company = request.user.company
        if request.user.branch:
            worker.branch = request.user.branch
        worker.save()
        return redirect(reverse("workforce:detail", args=[worker.pk]))
    return render(request, "workforce/form.html", {"form": form, "title": "Add Worker"})


@internal_required
def worker_edit(request, pk):
    worker = get_object_or_404(Worker, pk=pk)
    form = WorkerForm(request.POST or None, instance=worker)
    if form.is_valid():
        form.save()
        return redirect(reverse("workforce:detail", args=[worker.pk]))
    return render(request, "workforce/form.html",
                  {"form": form, "title": f"Edit – {worker.name}"})


@internal_required
def attendance_list(request):
    records = WorkerAttendance.objects.all().order_by("-date")
    return render(request, "workforce/attendance_list.html", {"records": records})


@internal_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(reverse("workforce:attendance_list"))
    return render(request, "workforce/attendance_form.html",
                  {"form": form, "title": "Mark Attendance"})


@internal_required
def assignment_list(request):
    assignments = WorkerAssignment.objects.filter(is_active=True)
    return render(request, "workforce/assignment_list.html",
                  {"assignments": assignments})


@internal_required
def assignment_create(request):
    form = AssignmentForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(reverse("workforce:assignment_list"))
    return render(request, "workforce/assignment_form.html",
                  {"form": form, "title": "Assign Worker"})


@internal_required
def payment_list(request):
    payments = WorkerPayment.objects.all().order_by("-created_at")
    return render(request, "workforce/payment_list.html", {"payments": payments})


@internal_required
def payment_create(request):
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(reverse("workforce:payment_list"))
    return render(request, "workforce/payment_form.html",
                  {"form": form, "title": "Worker Payment"})
