"""Notifications admin, views, URL routes."""
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.mixins import internal_required
from crm.models import Customer
from .models import NotificationTemplate, NotificationLog


# ---------- Default templates seeded at first run ----------
DEFAULT_TEMPLATES = [
    ("Booking Confirmation", "whatsapp", "booking_confirmation",
     "Booking Confirmed",
     "Hi {customer_name}, your booking for {service} on {date} is confirmed. "
     "Inspector {inspector} will visit your site. – {company_name}"),
    ("Inspection Scheduled", "whatsapp", "inspection_scheduled",
     "Inspection Scheduled",
     "Dear {customer_name}, site inspection scheduled for {date} at {time}. "
     "Please ensure access to all rooms. – {company_name}"),
    ("Quotation Sent", "whatsapp", "quotation_sent",
     "Quotation Ready",
     "Hi {customer_name}, your quotation {quote_number} for ₹{amount} is ready. "
     "Please review and approve. Valid until {valid_until}. – {company_name}"),
    ("Quotation Approved", "sms", "quotation_approved",
     "Quotation Approved",
     "Dear {customer_name}, thank you for approving quotation {quote_number}. "
     "We will start your project shortly. – {company_name}"),
    ("Payment Received", "sms", "payment_received",
     "Payment Received",
     "Dear {customer_name}, we received your payment of ₹{amount} via {method} "
     "(Ref: {reference}). Thank you! – {company_name}"),
    ("Payment Reminder", "sms", "payment_reminder",
     "Payment Reminder",
     "Dear {customer_name}, your invoice {invoice_number} has ₹{amount} outstanding. "
     "Due date: {due_date}. Please arrange payment. – {company_name}"),
    ("Project Started", "whatsapp", "project_started",
     "Project Started",
     "Hi {customer_name}, work on your project {project_number} has started today. "
     "Project Manager: {manager}. Expected completion: {end_date}. – {company_name}"),
    ("Project Completed", "whatsapp", "project_completed",
     "Project Completed",
     "Dear {customer_name}, your project {project_number} is complete. "
     "Please inspect the work and share feedback. Warranty valid till {warranty_end}. – {company_name}"),
    ("Warranty Expiry", "sms", "warranty_expiry",
     "Warranty Expiring",
     "Dear {customer_name}, your paint warranty expires on {warranty_end}. "
     "Book maintenance now to keep your walls fresh. – {company_name}"),
    ("Maintenance Reminder", "email", "maintenance_reminder",
     "Time for your annual maintenance",
     "Dear {customer_name},\n\nThis is a reminder that your annual painting maintenance "
     "is due on {next_due_date}.\n\nBook now to keep your walls looking new.\n\nRegards,\n{company_name}"),
]


def seed_default_templates(company):
    """Idempotent: creates default templates if none exist."""
    if NotificationTemplate.objects.filter(company=company).exists():
        return
    for name, channel, purpose, subject, body in DEFAULT_TEMPLATES:
        NotificationTemplate.objects.create(
            company=company, name=name, channel=channel,
            purpose=purpose, subject=subject, body=body,
        )


@admin.register(NotificationTemplate)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "purpose", "is_active")
    list_filter = ("channel", "purpose", "is_active")


@admin.register(NotificationLog)
class LogAdmin(admin.ModelAdmin):
    list_display = ("recipient", "channel", "status", "created_at", "sent_at")
    list_filter = ("channel", "status")


class SendNotificationForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=False,
                                       widget=forms.Select(attrs={"class": "form-select"}))
    recipient = forms.CharField(max_length=120, required=False,
                                  widget=forms.TextInput(attrs={"class": "form-control",
                                                                 "placeholder": "Phone / email (if no customer)"}))
    channel = forms.ChoiceField(choices=NotificationTemplate.Channel.choices,
                                 widget=forms.Select(attrs={"class": "form-select"}))
    template = forms.ModelChoiceField(queryset=NotificationTemplate.objects.filter(is_active=True),
                                       required=False,
                                       widget=forms.Select(attrs={"class": "form-select"}))
    subject = forms.CharField(max_length=255, required=False,
                               widget=forms.TextInput(attrs={"class": "form-control"}))
    body = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}))


@internal_required
def template_list(request):
    templates = NotificationTemplate.objects.all().order_by("name")
    return render(request, "notifications/template_list.html", {"templates": templates})


@internal_required
def template_create(request):
    class TemplateForm(forms.ModelForm):
        class Meta:
            model = NotificationTemplate
            fields = ("name", "channel", "purpose", "subject", "body", "is_active")
            widgets = {"body": forms.Textarea(attrs={"class": "form-control", "rows": 6})}
    form = TemplateForm(request.POST or None)
    if form.is_valid():
        t = form.save(commit=False)
        if request.user.company:
            t.company = request.user.company
        t.save()
        return redirect(reverse("notifications:template_list"))
    return render(request, "notifications/template_form.html",
                  {"form": form, "title": "New Template"})


@internal_required
def log_list(request):
    logs = NotificationLog.objects.all().order_by("-created_at")[:100]
    return render(request, "notifications/log_list.html", {"logs": logs})


@internal_required
def send_notification(request):
    form = SendNotificationForm(request.POST or None)
    if form.is_valid():
        log = NotificationLog(
            customer=form.cleaned_data["customer"],
            recipient=form.cleaned_data["recipient"] or
                       (form.cleaned_data["customer"].phone if form.cleaned_data["customer"] else ""),
            channel=form.cleaned_data["channel"],
            template=form.cleaned_data["template"],
            subject=form.cleaned_data["subject"],
            body=form.cleaned_data["body"],
            created_by=request.user,
        )
        # Simulate immediate send (sandbox: no real gateway)
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save()
        return redirect(reverse("notifications:log_list"))
    return render(request, "notifications/send.html", {"form": form, "title": "Send Notification"})


@internal_required
def dashboard(request):
    """Notifications overview."""
    from django.db.models import Count
    stats = {
        "templates": NotificationTemplate.objects.count(),
        "queued": NotificationLog.objects.filter(status="queued").count(),
        "sent": NotificationLog.objects.filter(status="sent").count(),
        "delivered": NotificationLog.objects.filter(status="delivered").count(),
        "failed": NotificationLog.objects.filter(status="failed").count(),
    }
    recent = NotificationLog.objects.all()[:10]
    return render(request, "notifications/dashboard.html", {"stats": stats, "recent": recent})
