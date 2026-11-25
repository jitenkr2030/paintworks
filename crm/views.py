"""CRM admin, forms and views."""
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from common.mixins import internal_required
from .models import Customer, Property, Lead, FollowUp, CustomerFeedback


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "customer_type", "city", "created_at")
    list_filter = ("customer_type", "city", "company")
    search_fields = ("name", "phone", "email", "address")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("label", "customer", "property_type", "city", "built_up_area")
    list_filter = ("property_type", "city")
    search_fields = ("label", "address", "customer__name")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "stage", "estimated_value", "assigned_to", "created_at")
    list_filter = ("stage", "source")
    search_fields = ("name", "phone", "service_required")


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("summary", "channel", "customer", "lead", "done_by", "created_at")
    list_filter = ("channel",)


@admin.register(CustomerFeedback)
class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = ("customer", "project", "rating", "created_at")


# ---------- Forms ----------
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("name", "customer_type", "email", "phone", "alt_phone",
                  "company_name", "gstin", "address", "city", "state", "pincode",
                  "source", "notes")


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ("label", "property_type", "address", "city", "state", "pincode",
                  "built_up_area", "bedrooms", "bathrooms", "notes")


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ("customer", "name", "phone", "email", "service_required",
                  "description", "stage", "source", "estimated_value",
                  "assigned_to", "next_followup_at")
        widgets = {
            "next_followup_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ("customer", "lead", "channel", "summary", "notes",
                  "next_followup_at")
        widgets = {
            "next_followup_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


# ---------- Views ----------
@internal_required
def customer_list(request):
    q = request.GET.get("q", "")
    customers = Customer.objects.all().select_related("company", "branch").order_by("-created_at")
    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    from common.export import paginate, export_queryset_to_excel
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Name", "name"), ("Type", "get_customer_type_display"),
            ("Phone", "phone"), ("Email", "email"),
            ("City", "city"), ("Source", "source"),
            ("Created", "created_at"),
        ]
        return export_queryset_to_excel(customers, cols, "customers", "Customers")
    page = paginate(customers, request, per_page=15)
    return render(request, "crm/customer_list.html",
                  {"customers": page.object_list, "page_obj": page,
                   "q": q})


@internal_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, "crm/customer_detail.html", {"customer": customer})


@internal_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        if request.user.company:
            customer.company = request.user.company
        if request.user.branch:
            customer.branch = request.user.branch
        customer.save()
        return redirect(reverse("crm:customer_detail", args=[customer.pk]))
    return render(request, "crm/customer_form.html", {"form": form, "title": "Add Customer"})


@internal_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("crm:customer_detail", args=[customer.pk]))
    return render(request, "crm/customer_form.html",
                  {"form": form, "title": f"Edit – {customer.name}"})


@internal_required
def property_create(request, customer_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    form = PropertyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        prop = form.save(commit=False)
        prop.customer = customer
        prop.save()
        return redirect(reverse("crm:customer_detail", args=[customer.pk]))
    return render(request, "crm/property_form.html",
                  {"form": form, "customer": customer, "title": "Add Property"})


@internal_required
def lead_list(request):
    from common.export import paginate, export_queryset_to_excel
    stage = request.GET.get("stage")
    leads = Lead.objects.all().order_by("-created_at")
    if stage:
        leads = leads.filter(stage=stage)
    stages = Lead.Stage.choices
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Name", "name"),
            ("Phone", "phone"),
            ("Service Required", "service_required"),
            ("Stage", "get_stage_display"),
            ("Estimated Value", "estimated_value"),
            ("Source", "source"),
            ("Assigned To", lambda l: l.assigned_to.display_name if l.assigned_to else ""),
            ("Created", "created_at"),
        ]
        return export_queryset_to_excel(leads, cols, "leads", "Leads")
    page = paginate(leads, request, per_page=20)
    return render(request, "crm/lead_list.html",
                  {"leads": page.object_list, "page_obj": page,
                   "stages": stages, "current_stage": stage})


@internal_required
def lead_create(request):
    form = LeadForm(request.POST or None)
    if form.is_valid():
        lead = form.save(commit=False)
        if request.user.company:
            lead.company = request.user.company
        if request.user.branch:
            lead.branch = request.user.branch
        lead.save()
        return redirect(reverse("crm:lead_list"))
    return render(request, "crm/lead_form.html", {"form": form, "title": "New Lead"})


@internal_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    form = LeadForm(request.POST or None, instance=lead)
    if form.is_valid():
        form.save()
        return redirect(reverse("crm:lead_list"))
    return render(request, "crm/lead_form.html",
                  {"form": form, "title": f"Edit Lead – {lead.name}"})


@internal_required
def followup_create(request):
    form = FollowUpForm(request.POST or None)
    if form.is_valid():
        fu = form.save(commit=False)
        fu.done_by = request.user
        fu.save()
        return redirect(request.META.get("HTTP_REFERER", reverse("crm:lead_list")))
    return render(request, "crm/followup_form.html", {"form": form, "title": "Log Follow-up"})
