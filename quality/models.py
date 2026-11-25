"""Quality control & after-sales app."""
from django.db import models
from django.conf import settings
from django.utils import timezone

from crm.models import Customer
from projects.models import Project


class QualityChecklist(models.Model):
    """Work quality inspection checklist."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="quality_checks")
    surface_preparation_ok = models.BooleanField(default=False)
    paint_shade_approved = models.BooleanField(default=False)
    finish_quality_ok = models.BooleanField(default=False)
    material_quality_verified = models.BooleanField(default=False)
    cleanup_done = models.BooleanField(default=False)
    customer_inspection_done = models.BooleanField(default=False)
    overall_rating = models.PositiveIntegerField(default=0,
                                                   help_text="1-5 overall rating")
    notes = models.TextField(blank=True)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL, null=True, blank=True)
    checked_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QC – {self.project.project_number}"


class Warranty(models.Model):
    """Service warranty records."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="warranties")
    warranty_period_months = models.PositiveIntegerField(default=12)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    coverage = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


class Complaint(models.Model):
    """Customer complaint / support ticket."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="complaints")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="complaints")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.OPEN)
    priority = models.CharField(max_length=20, choices=Priority.choices,
                                 default=Priority.MEDIUM)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name="assigned_complaints")
    resolution = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class MaintenanceReminder(models.Model):
    """Recurring maintenance service reminders."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="maintenance_reminders")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    service_type = models.CharField(max_length=120)
    next_due_date = models.DateField()
    interval_months = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
