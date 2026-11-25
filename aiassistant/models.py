"""V3: AI Assistant app — quotation generator + customer chatbot.

In this sandbox the 'AI' is implemented with deterministic rules and templates,
so it works offline. The hooks are designed so a real LLM API (e.g. OpenAI,
Anthropic, or z-ai SDK) can be dropped in by replacing the `generate_*` helpers.
"""
from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatSession(models.Model):
    """A customer chat session with the AI assistant."""

    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name="chat_sessions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.SET_NULL,
                              null=True, blank=True)
    session_key = models.CharField(max_length=100, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    summary = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Chat {self.session_key[:8]} – {self.customer or 'Anonymous'}"


class ChatMessage(models.Model):
    """Individual messages in a chat session."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE,
                                 related_name="messages")
    role = models.CharField(max_length=20, choices=Role.choices,
                             default=Role.USER)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True,
                               help_text="Detected intent: greeting, book_service, "
                                         "check_quote, complaint, pricing, etc.")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class AIQuotationRequest(models.Model):
    """An AI-generated quotation request — input measurements + photos."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATED = "generated", "Generated"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL,
                                  null=True, blank=True)
    inspection = models.ForeignKey("inspection.SiteInspection",
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    service_required = models.CharField(max_length=255, blank=True)
    property_type = models.CharField(max_length=50, blank=True)
    total_area = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rooms_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    generated_quotation = models.ForeignKey("estimation.Quotation",
                                             on_delete=models.SET_NULL,
                                             null=True, blank=True)
    ai_summary = models.TextField(blank=True,
                                    help_text="AI-generated human-readable summary.")
    suggested_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=2, default=0,
                                            help_text="0 to 100.")
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Quote Request #{self.pk} – {self.customer}"
