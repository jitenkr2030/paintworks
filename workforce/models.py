"""Workforce app: workers, attendance, assignments, productivity, payments."""
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company, Branch
from projects.models import Project, ProjectTask


class Worker(models.Model):
    """Worker / technician / subcontractor profile."""

    class WorkerType(models.TextChoices):
        PAINTER = "painter", "Painter"
        PLUMBER = "plumber", "Plumber"
        ELECTRICIAN = "electrician", "Electrician"
        CARPENTER = "carpenter", "Carpenter"
        MASON = "mason", "Mason"
        HELPER = "helper", "Helper"
        SUBCONTRACTOR = "subcontractor", "Subcontractor"

    class PaymentMode(models.TextChoices):
        DAILY = "daily", "Daily Wage"
        HOURLY = "hourly", "Hourly Wage"
        CONTRACT = "contract", "Contract-Based"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="worker_profile")
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    worker_type = models.CharField(max_length=20, choices=WorkerType.choices,
                                    default=WorkerType.PAINTER)
    skills = models.CharField(max_length=255, blank=True,
                               help_text="Comma-separated skills.")
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices,
                                     default=PaymentMode.DAILY)
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    id_proof = models.CharField(max_length=50, blank=True,
                                 help_text="Aadhaar / PAN / other ID")
    emergency_contact = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    joined_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} ({self.get_worker_type_display()})"


class WorkerAttendance(models.Model):
    """Daily check-in / check-out."""

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE,
                                related_name="attendance_records")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    date = models.DateField(default=timezone.now)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="present",
                                choices=[("present", "Present"),
                                          ("half_day", "Half Day"),
                                          ("absent", "Absent"),
                                          ("leave", "On Leave")])
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("worker", "date")
        ordering = ("-date",)


class WorkerAssignment(models.Model):
    """Project-wise worker assignment."""

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE,
                                related_name="assignments")
    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="worker_assignments")
    task = models.ForeignKey(ProjectTask, on_delete=models.SET_NULL,
                              null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)


class WorkerPayment(models.Model):
    """Payment statement / settlement."""

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE,
                                related_name="payments")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_on = models.DateField(null=True, blank=True)
    method = models.CharField(max_length=20, default="cash",
                                choices=[("cash", "Cash"),
                                          ("upi", "UPI"),
                                          ("bank", "Bank Transfer"),
                                          ("cheque", "Cheque")])
    status = models.CharField(max_length=20, default="pending",
                                choices=[("pending", "Pending"),
                                          ("paid", "Paid")])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WorkerLeave(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE,
                                related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
