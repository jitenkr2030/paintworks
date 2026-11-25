"""CRM app: customers, multi-property addresses, lead pipeline, communications."""
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company, Branch


class Customer(models.Model):
    """A customer (individual / residential society / commercial)."""

    class CustomerType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        RESIDENTIAL = "residential", "Residential Society"
        COMMERCIAL = "commercial", "Commercial"

    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="customers", null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="customer_profile",
        help_text="Linked login account (if registered).",
    )
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices,
                                      default=CustomerType.INDIVIDUAL)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    alt_phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True,
                                     help_text="For commercial customers.")
    gstin = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    source = models.CharField(max_length=50, blank=True,
                               help_text="website, walk-in, referral, advertisement, etc.")
    notes = models.TextField(blank=True)
    rating = models.PositiveIntegerField(default=0,
                                          help_text="Customer satisfaction rating 1-5")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def total_business(self):
        return sum(p.final_amount for p in self.projects.all() if p.final_amount)


class Property(models.Model):
    """Multiple property / site addresses for a customer."""

    class PropertyType(models.TextChoices):
        FLAT = "flat", "Flat / Apartment"
        HOUSE = "house", "Independent House"
        VILLA = "villa", "Villa"
        OFFICE = "office", "Office"
        SHOP = "shop", "Shop"
        COMMERCIAL = "commercial", "Commercial Building"
        SOCIETY = "society", "Residential Society"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="properties")
    label = models.CharField(max_length=120, help_text="e.g. 'Home', 'Shop at MG Road'")
    property_type = models.CharField(max_length=20, choices=PropertyType.choices,
                                      default=PropertyType.FLAT)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    built_up_area = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                         help_text="In square feet.")
    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} – {self.customer.name}"


class Lead(models.Model):
    """Lead pipeline with stage tracking and follow-up reminders."""

    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        INSPECTION = "inspection", "Inspection Scheduled"
        QUOTATION = "quotation", "Quotation Sent"
        NEGOTIATION = "negotiation", "Negotiation"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="leads", null=True, blank=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    service_required = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices,
                              default=Stage.NEW)
    source = models.CharField(max_length=50, blank=True)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_leads",
    )
    next_followup_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} – {self.get_stage_display()}"


class FollowUp(models.Model):
    """Call, WhatsApp, email and meeting follow-ups."""

    class Channel(models.TextChoices):
        CALL = "call", "Phone Call"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        VISIT = "visit", "Site Visit"
        MEETING = "meeting", "Meeting"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True,
                              related_name="followups")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True,
                                  related_name="followups")
    channel = models.CharField(max_length=20, choices=Channel.choices,
                                default=Channel.CALL)
    summary = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_channel_display()}: {self.summary}"


class CustomerFeedback(models.Model):
    """Customer ratings & reviews after service."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="feedbacks")
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="feedbacks")
    rating = models.PositiveIntegerField(help_text="1 to 5")
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
