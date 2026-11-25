"""Projects views."""
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from estimation.models import Quotation
from .models import Project, ProjectTask, DailyWorkReport, ProjectPhoto, CompletionCertificate


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("project_number", "title", "customer", "status",
                    "project_manager", "start_date", "end_date")
    list_filter = ("status",)


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "assigned_to", "due_date")


@admin.register(DailyWorkReport)
class DailyWorkReportAdmin(admin.ModelAdmin):
    list_display = ("project", "report_date", "submitted_by", "workers_count")


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("customer", "site", "quotation", "title", "description",
                  "project_manager", "start_date", "end_date", "final_amount",
                  "advance_received", "status", "progress_percent", "notes")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = ProjectTask
        fields = ("title", "room", "description", "assigned_to", "status",
                  "start_date", "due_date", "display_order")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyWorkReport
        fields = ("task", "report_date", "work_done", "workers_count",
                  "hours_worked", "material_used", "issues")
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date"}),
            "work_done": forms.Textarea(attrs={"rows": 3}),
            "material_used": forms.Textarea(attrs={"rows": 2}),
            "issues": forms.Textarea(attrs={"rows": 2}),
        }


def _generate_project_number(company=None):
    today = timezone.now().strftime("%Y%m%d")
    count = Project.objects.filter(created_at__date=timezone.now().date()).count() + 1
    prefix = (company.name[:3].upper() if company else "PRJ") if company else "PRJ"
    return f"{prefix}-{today}-{count:03d}"


@internal_required
def project_list(request):
    status = request.GET.get("status")
    qs = Project.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Project #", "project_number"),
            ("Title", "title"),
            ("Customer", lambda p: p.customer.name if p.customer else ""),
            ("Status", "get_status_display"),
            ("Manager", lambda p: p.project_manager.display_name if p.project_manager else ""),
            ("Start", "start_date"),
            ("End", "end_date"),
            ("Progress %", "progress_percent"),
            ("Final Amount", "final_amount"),
        ]
        return export_queryset_to_excel(qs, cols, "projects", "Projects")
    page = paginate(qs, request, per_page=20)
    return render(request, "projects/list.html",
                  {"projects": page.object_list, "page_obj": page,
                   "statuses": Project.Status.choices,
                   "current_status": status})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render(request, "projects/detail.html", {"project": project})


@internal_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    quote_id = request.GET.get("quotation")
    if quote_id:
        quote = Quotation.objects.filter(pk=quote_id, status="approved").first()
        if quote:
            form.initial.update({
                "quotation": quote, "customer": quote.customer,
                "title": f"Project for {quote.customer.name}",
                "final_amount": quote.grand_total,
                "advance_received": quote.advance_amount,
            })
    if form.is_valid():
        project = form.save(commit=False)
        if request.user.company:
            project.company = request.user.company
        if request.user.branch:
            project.branch = request.user.branch
        project.project_number = _generate_project_number(request.user.company)
        project.save()
        # If quotation, mark converted
        if project.quotation:
            project.quotation.status = "converted"
            project.quotation.save()
        return redirect(reverse("projects:detail", args=[project.pk]))
    return render(request, "projects/form.html", {"form": form, "title": "New Project"})


@internal_required
def project_add_task(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = TaskForm(request.POST or None)
    if form.is_valid():
        task = form.save(commit=False)
        task.project = project
        task.save()
        return redirect(reverse("projects:detail", args=[project.pk]))
    return render(request, "projects/task_form.html",
                  {"form": form, "project": project, "title": "Add Task"})


@internal_required
def project_task_status(request, pk, task_pk):
    if request.method == "POST":
        task = get_object_or_404(ProjectTask, pk=task_pk, project_id=pk)
        new_status = request.POST.get("status")
        if new_status in dict(ProjectTask.Status.choices):
            task.status = new_status
            if new_status == "done":
                task.completed_at = timezone.now()
            task.save()
    return redirect(reverse("projects:detail", args=[pk]))


@login_required
def project_add_report(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = DailyReportForm(request.POST or None)
    if form.is_valid():
        report = form.save(commit=False)
        report.project = project
        report.submitted_by = request.user
        report.save()
        return redirect(reverse("projects:detail", args=[project.pk]))
    return render(request, "projects/report_form.html",
                  {"form": form, "project": project, "title": "Daily Work Report"})


@login_required
def project_upload_photo(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        for f in request.FILES.getlist("photos"):
            ProjectPhoto.objects.create(
                project=project, image=f,
                photo_type=request.POST.get("photo_type", "during"),
                caption=request.POST.get("caption", ""),
                uploaded_by=request.user,
            )
    return redirect(reverse("projects:detail", args=[project.pk]))


@internal_required
def project_completion(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        cert, _ = CompletionCertificate.objects.get_or_create(project=project)
        cert.quality_approved = request.POST.get("quality_approved") == "on"
        cert.notes = request.POST.get("notes", "")
        if request.POST.get("customer_signed") == "on":
            cert.customer_signed = True
            cert.customer_signed_at = timezone.now()
        cert.save()
        project.status = "completed"
        project.actual_end = timezone.now().date()
        project.progress_percent = 100
        project.save()
    return redirect(reverse("projects:detail", args=[project.pk]))


@login_required
def worker_my_tasks(request):
    """Worker-facing task list."""
    tasks = ProjectTask.objects.filter(assigned_to=request.user).order_by("due_date")
    return render(request, "projects/my_tasks.html", {"tasks": tasks})


@login_required
def project_timeline(request, pk):
    """V2: Detailed project scheduling with timeline/Gantt-style view."""
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.all().order_by("display_order", "id")
    # Build a Gantt-style data structure
    from datetime import datetime, timedelta as _td
    timeline_start = project.start_date or project.created_at.date()
    timeline_end = project.end_date or (timeline_start + _td(days=30))
    total_days = max(1, (timeline_end - timeline_start).days)
    rows = []
    for t in tasks:
        start = t.start_date or timeline_start
        end = t.due_date or (start + _td(days=2))
        offset_days = max(0, (start - timeline_start).days)
        duration_days = max(1, (end - start).days)
        pct_offset = round(offset_days / total_days * 100, 2)
        pct_width = round(min(duration_days / total_days, 1) * 100, 2)
        rows.append({
            "task": t, "start": start, "end": end,
            "offset_days": offset_days, "duration_days": duration_days,
            "pct_offset": pct_offset, "pct_width": pct_width,
        })
    return render(request, "projects/timeline.html", {
        "project": project, "rows": rows,
        "timeline_start": timeline_start, "timeline_end": timeline_end,
        "total_days": total_days,
    })
