"""Services catalogue: full service taxonomy from the spec."""
from django.db import models
from django.utils.translation import gettext_lazy as _


class ServiceCategory(models.Model):
    """Top-level service groups: whitewash, painting, renovation, etc."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class")
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class ServiceSubcategory(models.Model):
    """Granular services like 'interior painting', 'modular kitchen', etc."""

    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE,
                                 related_name="subcategories")
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    default_unit = models.CharField(
        max_length=20, default="sq_ft",
        choices=[("sq_ft", "Square Feet"), ("sq_m", "Square Metre"),
                 ("rft", "Running Feet"), ("job", "Per Job"),
                 ("item", "Per Item"), ("hour", "Per Hour")],
    )
    default_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class CoverageRate(models.Model):
    """Configurable material coverage rates used by the estimation engine."""

    material_name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20, default="sq_ft")
    coverage_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, default=1.0,
        help_text="Area covered per single unit of material (e.g. 1 litre covers 120 sq ft)."
    )
    coats = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.material_name} – {self.coverage_per_unit} {self.unit}/unit"
