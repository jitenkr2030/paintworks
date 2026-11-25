"""Billing app: invoices, GST, payments, receipts, profitability."""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import Company, Branch
from crm.models import Customer
from projects.models import Project
from inventory.models import Supplier


class Invoice(models.Model):
    """GST-compliant customer invoice."""

    class Type(models.TextChoices):
        PROFORMA = "proforma", "Proforma"
        TAX = "tax", "Tax Invoice"
        FINAL = "final", "Final Bill"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIAL = "partial", "Partially Paid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=30, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="invoices")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_type = models.CharField(max_length=20, choices=Type.choices,
                                     default=Type.TAX)
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    notes = models.TextField(blank=True)
    transport_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    misc_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.0)
    created_at = models.DateTimeField(auto_now_add=True)

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
    def amount_paid(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def balance_due(self):
        return self.grand_total - self.amount_paid

    def __str__(self):
        return self.invoice_number


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, default="sq_ft")
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def amount(self):
        return round(self.quantity * self.rate, 2)


class PaymentReceipt(models.Model):
    """A payment received against an invoice."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE,
                                 related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_on = models.DateField(default=timezone.now)
    method = models.CharField(max_length=20,
                                choices=[("cash", "Cash"), ("upi", "UPI"),
                                          ("bank", "Bank Transfer"),
                                          ("card", "Card"), ("cheque", "Cheque")],
                                default="upi")
    reference = models.CharField(max_length=100, blank=True,
                                  help_text="Transaction ID / cheque no.")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SupplierBill(models.Model):
    """Supplier bill for expenses."""

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE,
                                  related_name="bills")
    bill_number = models.CharField(max_length=50)
    bill_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid = models.BooleanField(default=False)
    paid_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CreditNote(models.Model):
    """Credit note / refund issued to a customer."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="credit_notes")
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    issued_on = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)


class Expense(models.Model):
    """General business expense."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=80, blank=True,
                                 help_text="transport, fuel, tools, food, etc.")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    incurred_on = models.DateField(default=timezone.now)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.SET_NULL, null=True, blank=True)
    receipt = models.FileField(upload_to="expense_receipts/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
