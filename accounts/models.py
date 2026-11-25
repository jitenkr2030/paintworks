"""Accounts app: custom User model, RBAC, six-portal roles."""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    """Six connected portals described in the application architecture."""
    SUPER_ADMIN = "super_admin", _("Super Admin")
    BUSINESS_OWNER = "business_owner", _("Business Owner")
    OFFICE_STAFF = "office_staff", _("Office Staff")
    PROJECT_MANAGER = "project_manager", _("Project Manager")
    WORKER = "worker", _("Worker / Technician")
    CUSTOMER = "customer", _("Customer")


class Company(models.Model):
    """A business that uses the platform. Supports multi-company SaaS."""

    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=255, blank=True)
    gstin = models.CharField(max_length=20, blank=True, help_text="GST Identification Number")
    pan = models.CharField(max_length=12, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class Branch(models.Model):
    """A branch / office of a company. Supports multi-branch businesses."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="managed_branches",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class User(AbstractUser):
    """Custom user with role, company and branch linkage."""

    role = models.CharField(
        max_length=30, choices=Role.choices, default=Role.CUSTOMER
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="users",
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="users",
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_staff_user = models.BooleanField(
        default=False,
        help_text="True for any internal company-side role (owner/staff/pm/worker).",
    )

    # Customer-specific extras
    customer_type = models.CharField(
        max_length=20, blank=True,
        choices=[("individual", "Individual"), ("residential", "Residential Society"),
                 ("commercial", "Commercial")],
    )

    REQUIRED_FIELDS = ["email"]

    @property
    def display_name(self):
        full = self.get_full_name().strip()
        return full or self.username

    @property
    def is_customer(self):
        return self.role == Role.CUSTOMER

    @property
    def is_internal(self):
        return self.role in {
            Role.SUPER_ADMIN, Role.BUSINESS_OWNER,
            Role.OFFICE_STAFF, Role.PROJECT_MANAGER, Role.WORKER,
        }

    @property
    def is_management(self):
        return self.role in {
            Role.SUPER_ADMIN, Role.BUSINESS_OWNER, Role.OFFICE_STAFF,
        }

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"
