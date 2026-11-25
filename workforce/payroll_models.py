"""V2: Payroll & contractor settlement extensions to workforce."""
from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.utils import timezone

from workforce.models import Worker, WorkerAttendance, WorkerPayment
from projects.models import Project


class PayrollCycle(models.Model):
    """A payroll cycle (weekly / fortnightly / monthly)."""

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"

    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE,
                                 null=True, blank=True)
    name = models.CharField(max_length=120)
    frequency = models.CharField(max_length=20, choices=Frequency.choices,
                                  default=Frequency.MONTHLY)
    start_date = models.DateField()
    end_date = models.DateField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-start_date",)

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class PayrollEntry(models.Model):
    """One row per worker per payroll cycle."""

    cycle = models.ForeignKey(PayrollCycle, on_delete=models.CASCADE,
                               related_name="entries")
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE,
                                related_name="payroll_entries")
    present_days = models.PositiveIntegerField(default=0)
    absent_days = models.PositiveIntegerField(default=0)
    leave_days = models.PositiveIntegerField(default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    paid_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("cycle", "worker")

    def __str__(self):
        return f"{self.worker.name} – {self.cycle.name}"

    def save(self, *args, **kwargs):
        # Auto-calc net payable
        self.net_payable = (self.base_amount + self.overtime_amount +
                            self.bonus - self.deductions)
        super().save(*args, **kwargs)


class ContractorSettlement(models.Model):
    """Settlement with a subcontractor for a project or period."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    contractor = models.ForeignKey(Worker, on_delete=models.CASCADE,
                                    related_name="contractor_settlements",
                                    limit_choices_to={"worker_type": "subcontractor"})
    project = models.ForeignKey(Project, on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 related_name="contractor_settlements")
    period_start = models.DateField()
    period_end = models.DateField()
    agreed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    work_completed_percent = models.PositiveIntegerField(default=0)
    payable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    paid_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Pro-rata based on work completed
        if self.agreed_amount and self.work_completed_percent:
            self.payable_amount = (self.agreed_amount *
                                    Decimal(str(self.work_completed_percent)) /
                                    Decimal("100"))
        super().save(*args, **kwargs)
