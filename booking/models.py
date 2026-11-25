"""Booking app: online service booking & appointment scheduling."""
from django.db import models
from django.conf import settings

from accounts.models import Company, Branch
from crm.models import Customer, Property
from services.models import ServiceSubcategory


class Booking(models.Model):
    """Customer-initiated service booking."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        ASSIGNED = "assigned", "Inspector Assigned"
        INSPECTED = "inspected", "Inspected"
        QUOTED = "quoted", "Quotation Sent"
        APPROVED = "approved", "Quotation Approved"
        REJECTED = "rejected", "Quotation Rejected"
        CONVERTED = "converted", "Converted to Project"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="bookings")
    site = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    services = models.ManyToManyField(ServiceSubcategory, blank=True, related_name="bookings")
    title = models.CharField(max_length=200, default="Service Booking")
    property_type = models.CharField(max_length=20, blank=True)
    rooms_description = models.TextField(blank=True,
                                          help_text="Room-wise service selection notes.")
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    photos_uploads = models.TextField(blank=True,
                                       help_text="Comma-separated list of photo paths.")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.NEW)
    assigned_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_bookings",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bookings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Booking #{self.pk} – {self.customer.name}"


class BookingPhoto(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="booking_photos/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
