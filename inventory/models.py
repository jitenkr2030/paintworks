"""Inventory app: materials, suppliers, purchase orders, stock."""
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company, Branch
from projects.models import Project


class Supplier(models.Model):
    """Vendor / supplier of materials."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Material(models.Model):
    """A material / SKU in the catalogue."""

    class Unit(models.TextChoices):
        LITRE = "litre", "Litre"
        KG = "kg", "Kilogram"
        BAG = "bag", "Bag"
        PIECE = "piece", "Piece"
        BOX = "box", "Box"
        ROLL = "roll", "Roll"
        SET = "set", "Set"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=80, blank=True,
                                 help_text="paint, primer, putty, tools, electrical, plumbing, etc.")
    brand = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.LITRE)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    batch_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    @property
    def needs_reorder(self):
        return self.current_stock <= self.minimum_stock

    def __str__(self):
        return f"{self.name} ({self.brand})" if self.brand else self.name


class PurchaseOrder(models.Model):
    """Purchase order placed on a supplier."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIAL = "partial", "Partially Received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    po_number = models.CharField(max_length=30, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE,
                                  related_name="purchase_orders")
    order_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        return sum(line.amount for line in self.lines.all())

    def __str__(self):
        return self.po_number


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE,
                            related_name="lines")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def amount(self):
        return round(self.quantity * self.rate, 2)


class MaterialIssue(models.Model):
    """Stock issued to a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                 related_name="material_issues")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True)
    issued_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True)


class MaterialReturn(models.Model):
    """Material returned from project to stock."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    condition = models.CharField(max_length=20, default="good",
                                  choices=[("good", "Good"), ("damaged", "Damaged"),
                                           ("wastage", "Wastage")])
    returned_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True)
