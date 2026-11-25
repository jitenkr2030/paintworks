"""Inspection app: site inspection, measurements, area auto-calc."""
from django.db import models
from django.conf import settings

from booking.models import Booking
from crm.models import Property


class SiteInspection(models.Model):
    """A site inspection visit scheduled for a booking."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE,
                                 related_name="inspections")
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name="inspections_done")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.SCHEDULED)
    overall_condition = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    customer_approved = models.BooleanField(default=False)
    customer_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Inspection #{self.pk} – Booking #{self.booking_id}"


class RoomMeasurement(models.Model):
    """Room-wise wall / ceiling / opening measurements with area auto-calc."""

    inspection = models.ForeignKey(SiteInspection, on_delete=models.CASCADE,
                                    related_name="room_measurements")
    room_name = models.CharField(max_length=120, help_text="e.g. Living Room, Bedroom 1")
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                  help_text="In feet.")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                 help_text="In feet.")
    height = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                  help_text="Wall height in feet.")
    door_width = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    door_height = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    door_count = models.PositiveIntegerField(default=0)
    window_width = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    window_height = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    window_count = models.PositiveIntegerField(default=0)
    ceiling_area = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    surface_condition = models.CharField(max_length=255, blank=True,
                                          help_text="Existing paint/plaster condition.")
    dampness_observed = models.BooleanField(default=False)
    cracks_observed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    @property
    def wall_area(self):
        """Perimeter × height."""
        perimeter = 2 * (self.length + self.width)
        return round(perimeter * self.height, 2)

    @property
    def openings_area(self):
        """Combined door + window deduction."""
        doors = self.door_width * self.door_height * self.door_count
        windows = self.window_width * self.window_height * self.window_count
        return round(doors + windows, 2)

    @property
    def net_paint_area(self):
        return round(self.wall_area - self.openings_area, 2)

    @property
    def total_ceiling_area(self):
        if self.ceiling_area:
            return self.ceiling_area
        return round(self.length * self.width, 2)

    def __str__(self):
        return f"{self.room_name} – {self.inspection_id}"


class InspectionPhoto(models.Model):
    """Before-work photographs."""

    inspection = models.ForeignKey(SiteInspection, on_delete=models.CASCADE,
                                    related_name="photos")
    image = models.ImageField(upload_to="inspection_photos/")
    caption = models.CharField(max_length=255, blank=True)
    photo_type = models.CharField(max_length=20, default="before",
                                   choices=[("before", "Before"),
                                            ("during", "During"),
                                            ("after", "After")])
    uploaded_at = models.DateTimeField(auto_now_add=True)
