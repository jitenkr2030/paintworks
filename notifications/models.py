"""Notifications app: WhatsApp / SMS / email templates & queue (V2)."""
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company
from crm.models import Customer


class NotificationTemplate(models.Model):
    """Reusable message templates with placeholders like {name}, {amount}."""

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"

    class Purpose(models.TextChoices):
        BOOKING_CONFIRMATION = "booking_confirmation", "Booking Confirmation"
        INSPECTION_SCHEDULED = "inspection_scheduled", "Inspection Scheduled"
        QUOTATION_SENT = "quotation_sent", "Quotation Sent"
        QUOTATION_APPROVED = "quotation_approved", "Quotation Approved"
        PAYMENT_RECEIVED = "payment_received", "Payment Received"
        PAYMENT_REMINDER = "payment_reminder", "Payment Reminder"
        PROJECT_STARTED = "project_started", "Project Started"
        PROJECT_COMPLETED = "project_completed", "Project Completed"
        WORKER_ASSIGNMENT = "worker_assignment", "Worker Assignment"
        WARRANTY_EXPIRY = "warranty_expiry", "Warranty Expiry"
        MAINTENANCE_REMINDER = "maintenance_reminder", "Maintenance Reminder"
        CUSTOM = "custom", "Custom"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=20, choices=Channel.choices,
                                default=Channel.WHATSAPP)
    purpose = models.CharField(max_length=40, choices=Purpose.choices,
                                default=Purpose.CUSTOM)
    subject = models.CharField(max_length=255, blank=True,
                                help_text="Email subject; ignored for SMS/WhatsApp.")
    body = models.TextField(help_text="Use {placeholders} like {customer_name}, {amount}, {date}.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.name}"

    def render(self, context):
        """Simple placeholder substitution."""
        text = self.body
        for key, value in context.items():
            text = text.replace("{" + key + "}", str(value))
        return text


class NotificationLog(models.Model):
    """Outbound notification queue / log."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL,
                                  null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL,
                                  null=True, blank=True)
    recipient = models.CharField(max_length=120,
                                  help_text="Phone number or email address.")
    channel = models.CharField(max_length=20, choices=NotificationTemplate.Channel.choices,
                                default=NotificationTemplate.Channel.WHATSAPP)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.QUEUED)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.recipient} – {self.status}"
