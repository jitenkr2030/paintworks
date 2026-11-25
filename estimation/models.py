"""Estimation app: quotation engine with material/labour calculations."""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company, Branch
from booking.models import Booking
from crm.models import Customer
from inspection.models import SiteInspection
from services.models import ServiceSubcategory


class Quotation(models.Model):
    """A professional quotation generated from measurements."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent to Customer"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CONVERTED = "converted", "Converted to Project"

    quote_number = models.CharField(max_length=30, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="quotations")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    inspection = models.ForeignKey(SiteInspection, on_delete=models.SET_NULL,
                                    null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    quotation_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True,
                                         default="1. 50% advance with work order.\n"
                                                 "2. Balance on completion.\n"
                                                 "3. Taxes as applicable.\n"
                                                 "4. Valid for 30 days.")
    transport_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    misc_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.0,
                                    help_text="GST percentage.")
    advance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50.0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.quote_number} – {self.customer.name}"

    @property
    def subtotal(self):
        return sum(line.amount for line in self.lines.all())

    @property
    def taxable_value(self):
        return (self.subtotal + self.transport_charges + self.misc_charges) - self.discount

    @property
    def tax_amount(self):
        return round(self.taxable_value * (self.tax_rate / Decimal(100)), 2)

    @property
    def grand_total(self):
        return self.taxable_value + self.tax_amount

    @property
    def advance_amount(self):
        return round(self.grand_total * (self.advance_percentage / Decimal(100)), 2)

    @property
    def balance_amount(self):
        return self.grand_total - self.advance_amount


class QuotationLine(models.Model):
    """Line item – either material or labour, by unit and rate."""

    class LineType(models.TextChoices):
        MATERIAL = "material", "Material"
        LABOUR = "labour", "Labour"
        CUSTOM = "custom", "Custom Work"

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE,
                                   related_name="lines")
    service = models.ForeignKey(ServiceSubcategory, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    room = models.CharField(max_length=120, blank=True,
                            help_text="Optional room label.")
    description = models.CharField(max_length=255)
    line_type = models.CharField(max_length=20, choices=LineType.choices,
                                 default=LineType.MATERIAL)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, default="sq_ft")
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def amount(self):
        return round(self.quantity * self.rate, 2)

    def __str__(self):
        return f"{self.description} – {self.quantity} {self.unit} @ {self.rate}"
