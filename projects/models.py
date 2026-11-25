"""Projects app: project creation, work orders, tasks, progress."""
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company, Branch
from crm.models import Customer, Property
from estimation.models import Quotation


class Project(models.Model):
    """A project created from an approved quotation."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    project_number = models.CharField(max_length=30, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="projects")
    site = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    quotation = models.OneToOneField(Quotation, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="project")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PLANNED)
    project_manager = models.ForeignKey(settings.AUTH_USER_MODEL,
                                         on_delete=models.SET_NULL,
                                         null=True, blank=True,
                                         related_name="managed_projects")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    progress_percent = models.PositiveIntegerField(default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.project_number} – {self.title}"

    @property
    def is_delayed(self):
        if self.end_date and self.status != self.Status.COMPLETED:
            return timezone.now().date() > self.end_date
        return False


class ProjectTask(models.Model):
    """Room-wise or service-wise task allocation."""

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="tasks")
    title = models.CharField(max_length=200)
    room = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name="assigned_tasks")
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.TODO)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.title} – {self.project.project_number}"


class DailyWorkReport(models.Model):
    """Daily work progress reports submitted by workers / PMs."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="daily_reports")
    task = models.ForeignKey(ProjectTask, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="daily_reports")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True)
    report_date = models.DateField(default=timezone.now)
    work_done = models.TextField()
    workers_count = models.PositiveIntegerField(default=0)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    material_used = models.TextField(blank=True)
    issues = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProjectPhoto(models.Model):
    """Before / during / after photos."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="photos")
    image = models.ImageField(upload_to="project_photos/")
    caption = models.CharField(max_length=255, blank=True)
    photo_type = models.CharField(max_length=20, default="during",
                                   choices=[("before", "Before"),
                                            ("during", "During"),
                                            ("after", "After")])
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class CompletionCertificate(models.Model):
    """Customer sign-off / completion certificate."""

    project = models.OneToOneField(Project, on_delete=models.CASCADE,
                                    related_name="completion_certificate")
    issued_date = models.DateField(default=timezone.now)
    customer_signed = models.BooleanField(default=False)
    customer_signed_at = models.DateTimeField(null=True, blank=True)
    quality_approved = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
