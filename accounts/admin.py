"""Accounts admin and registration forms."""
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User, Company, Branch


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "email", "role", "company", "branch", "phone")

    def clean_password2(self):
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords don't match")
        return self.cleaned_data["password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "gstin", "city", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "legal_name", "gstin", "email")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "city", "manager", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "city", "code")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "email", "phone",
                                  "address", "city", "avatar")}),
        ("Role & Org", {"fields": ("role", "company", "branch",
                                    "is_staff_user", "customer_type")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",
                                     "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "role", "company", "branch", "phone",
                       "password1", "password2"),
        }),
    )
    list_display = ("username", "email", "role", "company", "branch", "is_active")
    list_filter = ("role", "company", "branch", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
