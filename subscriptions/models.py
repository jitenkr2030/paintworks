"""V3: SaaS subscription management — plans, subscriptions, usage, invoices."""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company


class SubscriptionPlan(models.Model):
    """A SaaS subscription plan (Starter, Professional, Enterprise)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=5)
    max_branches = models.PositiveIntegerField(default=1)
    max_projects_per_month = models.PositiveIntegerField(default=10)
    features = models.JSONField(default=list, blank=True,
                                  help_text="List of feature strings included in the plan.")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (₹{self.monthly_price}/mo)"


class Subscription(models.Model):
    """A company's active subscription to a plan."""

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    company = models.OneToOneField(Company, on_delete=models.CASCADE,
                                     related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT,
                              related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.TRIAL)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices,
                                       default=BillingCycle.MONTHLY)
    started_at = models.DateField(default=timezone.now)
    current_period_start = models.DateField(default=timezone.now)
    current_period_end = models.DateField(null=True, blank=True)
    trial_ends_at = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} – {self.plan.name} ({self.status})"


class SubscriptionInvoice(models.Model):
    """SaaS billing invoice issued to a company for their subscription."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        VOID = "void", "Void"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE,
                                       related_name="invoices")
    invoice_number = models.CharField(max_length=40, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    issued_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=30, blank=True,
                                       help_text="upi / card / netbanking / etc.")
    payment_reference = models.CharField(max_length=120, blank=True)

    def save(self, *args, **kwargs):
        self.grand_total = self.amount + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} – {self.subscription.company.name}"


class FeatureUsage(models.Model):
    """Track usage of metered features per subscription period."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE,
                                       related_name="usage_records")
    feature = models.CharField(max_length=80,
                                help_text="users, branches, projects, storage_mb, etc.")
    period_start = models.DateField()
    period_end = models.DateField()
    used = models.PositiveIntegerField(default=0)
    limit = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    @property
    def exceeds_limit(self):
        return self.limit > 0 and self.used > self.limit

    class Meta:
        unique_together = ("subscription", "feature", "period_start")
