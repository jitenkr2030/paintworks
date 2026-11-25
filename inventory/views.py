"""Inventory views."""
from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from projects.models import Project
from .models import Supplier, Material, PurchaseOrder, PurchaseOrderLine, MaterialIssue, MaterialReturn


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "city", "is_active")


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "unit", "current_stock",
                    "minimum_stock", "needs_reorder")
    list_filter = ("category", "brand")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "supplier", "order_date", "status", "total")


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("name", "contact_person", "phone", "email", "gstin",
                  "address", "city", "is_active")


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ("name", "sku", "category", "brand", "unit", "purchase_price",
                  "selling_price", "current_stock", "minimum_stock",
                  "batch_number", "is_active")


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ("supplier", "order_date", "expected_date", "status", "notes")
        widgets = {
            "order_date": forms.DateInput(attrs={"type": "date"}),
            "expected_date": forms.DateInput(attrs={"type": "date"}),
        }


class POLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ("material", "quantity", "rate", "received_quantity")


class MaterialIssueForm(forms.ModelForm):
    class Meta:
        model = MaterialIssue
        fields = ("project", "material", "quantity", "notes")


class MaterialReturnForm(forms.ModelForm):
    class Meta:
        model = MaterialReturn
        fields = ("project", "material", "quantity", "condition", "notes")


@internal_required
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by("name")
    return render(request, "inventory/supplier_list.html", {"suppliers": suppliers})


@internal_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        sup = form.save(commit=False)
        if request.user.company:
            sup.company = request.user.company
        sup.save()
        return redirect(reverse("inventory:supplier_list"))
    return render(request, "inventory/supplier_form.html",
                  {"form": form, "title": "Add Supplier"})


@internal_required
def material_list(request):
    q = request.GET.get("q", "")
    materials = Material.objects.all().order_by("name")
    if q:
        materials = materials.filter(name__icontains=q) | materials.filter(brand__icontains=q)
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Name", "name"),
            ("Brand", "brand"),
            ("Category", "category"),
            ("SKU", "sku"),
            ("Unit", "get_unit_display"),
            ("Current Stock", "current_stock"),
            ("Minimum Stock", "minimum_stock"),
            ("Reorder", lambda m: "Yes" if m.needs_reorder else "No"),
        ]
        return export_queryset_to_excel(materials, cols, "materials", "Materials")
    page = paginate(materials, request, per_page=20)
    return render(request, "inventory/material_list.html",
                  {"materials": page.object_list, "page_obj": page, "q": q})


@internal_required
def material_create(request):
    form = MaterialForm(request.POST or None)
    if form.is_valid():
        m = form.save(commit=False)
        if request.user.company:
            m.company = request.user.company
        if request.user.branch:
            m.branch = request.user.branch
        m.save()
        return redirect(reverse("inventory:material_list"))
    return render(request, "inventory/material_form.html",
                  {"form": form, "title": "Add Material"})


@internal_required
def material_edit(request, pk):
    m = get_object_or_404(Material, pk=pk)
    form = MaterialForm(request.POST or None, instance=m)
    if form.is_valid():
        form.save()
        return redirect(reverse("inventory:material_list"))
    return render(request, "inventory/material_form.html",
                  {"form": form, "title": f"Edit – {m.name}"})


@internal_required
def po_list(request):
    pos = PurchaseOrder.objects.all().order_by("-created_at")
    return render(request, "inventory/po_list.html", {"pos": pos})


@internal_required
def po_detail(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    return render(request, "inventory/po_detail.html", {"po": po})


@internal_required
def po_create(request):
    form = PurchaseOrderForm(request.POST or None)
    if form.is_valid():
        po = form.save(commit=False)
        if request.user.company:
            po.company = request.user.company
        if request.user.branch:
            po.branch = request.user.branch
        po.created_by = request.user
        today = timezone.now().strftime("%Y%m%d")
        n = PurchaseOrder.objects.filter(created_at__date=timezone.now().date()).count() + 1
        po.po_number = f"PO-{today}-{n:03d}"
        po.save()
        return redirect(reverse("inventory:po_detail", args=[po.pk]))
    return render(request, "inventory/po_form.html", {"form": form, "title": "New Purchase Order"})


@internal_required
def po_add_line(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    form = POLineForm(request.POST or None)
    if form.is_valid():
        line = form.save(commit=False)
        line.po = po
        line.save()
        # Update stock if received
        if line.received_quantity > 0:
            line.material.current_stock += line.received_quantity
            line.material.save()
        return redirect(reverse("inventory:po_detail", args=[po.pk]))
    return render(request, "inventory/po_line_form.html",
                  {"form": form, "po": po, "title": "Add PO Line"})


@internal_required
def material_issue_list(request):
    issues = MaterialIssue.objects.all().order_by("-issued_at")
    return render(request, "inventory/issue_list.html", {"issues": issues})


@internal_required
def material_issue_create(request):
    form = MaterialIssueForm(request.POST or None)
    if form.is_valid():
        issue = form.save(commit=False)
        issue.issued_by = request.user
        issue.save()
        # Deduct from stock
        issue.material.current_stock -= issue.quantity
        issue.material.save()
        return redirect(reverse("inventory:material_issue_list"))
    return render(request, "inventory/issue_form.html",
                  {"form": form, "title": "Issue Material"})


@internal_required
def material_return_list(request):
    returns = MaterialReturn.objects.all().order_by("-returned_at")
    return render(request, "inventory/return_list.html", {"returns": returns})


@internal_required
def material_return_create(request):
    form = MaterialReturnForm(request.POST or None)
    if form.is_valid():
        ret = form.save()
        if ret.condition == "good":
            ret.material.current_stock += ret.quantity
            ret.material.save()
        return redirect(reverse("inventory:material_return_list"))
    return render(request, "inventory/return_form.html",
                  {"form": form, "title": "Return Material"})
