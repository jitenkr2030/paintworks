"""Billing views: invoices, payments, profitability, PDF."""
from decimal import Decimal
from io import BytesIO

from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle,
                                 Spacer, HRFlowable)
from reportlab.lib.enums import TA_CENTER

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from crm.models import Customer
from projects.models import Project
from .models import (Invoice, InvoiceLine, PaymentReceipt, SupplierBill,
                     CreditNote, Expense)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "invoice_type", "status",
                    "grand_total", "amount_paid", "balance_due")
    list_filter = ("status", "invoice_type")


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "received_on", "method")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "project", "amount", "incurred_on")


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ("customer", "project", "invoice_type", "invoice_date",
                  "due_date", "transport_charges", "misc_charges", "discount",
                  "tax_rate", "notes")
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class InvoiceLineForm(forms.ModelForm):
    class Meta:
        model = InvoiceLine
        fields = ("description", "quantity", "unit", "rate")


class PaymentForm(forms.ModelForm):
    class Meta:
        model = PaymentReceipt
        fields = ("amount", "received_on", "method", "reference", "notes")
        widgets = {"received_on": forms.DateInput(attrs={"type": "date"})}


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ("project", "category", "description", "amount",
                  "incurred_on", "notes")
        widgets = {"incurred_on": forms.DateInput(attrs={"type": "date"})}


def _generate_invoice_number(company=None, inv_type="tax"):
    today = timezone.now().strftime("%Y%m%d")
    n = Invoice.objects.filter(created_at__date=timezone.now().date()).count() + 1
    prefix = (company.name[:3].upper() if company else "INV") if company else "INV"
    code = {"proforma": "PRF", "tax": "INV", "final": "FIN"}.get(inv_type, "INV")
    return f"{prefix}-{code}-{today}-{n:03d}"


@internal_required
def invoice_list(request):
    status = request.GET.get("status")
    qs = Invoice.objects.all().select_related("customer", "project").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Invoice #", "invoice_number"),
            ("Customer", lambda i: i.customer.name if i.customer else ""),
            ("Date", "invoice_date"),
            ("Status", "get_status_display"),
            ("Grand Total", "grand_total"),
            ("Amount Paid", "amount_paid"),
            ("Balance Due", "balance_due"),
        ]
        return export_queryset_to_excel(qs, cols, "invoices", "Invoices")
    page = paginate(qs, request, per_page=20)
    return render(request, "billing/invoice_list.html",
                  {"invoices": page.object_list, "page_obj": page,
                   "statuses": Invoice.Status.choices,
                   "current_status": status})


@login_required
def invoice_detail(request, pk):
    """Allow internal users OR the linked customer to view an invoice."""
    inv = get_object_or_404(Invoice.objects.select_related("customer", "project", "company"), pk=pk)
    if not request.user.is_internal:
        try:
            if not (inv.customer and inv.customer.user_id == request.user.id):
                return redirect(reverse("dashboard"))
        except Exception:
            return redirect(reverse("dashboard"))
    return render(request, "billing/invoice_detail.html",
                  {"invoice": inv, "is_internal": request.user.is_internal})


@internal_required
def invoice_create(request):
    form = InvoiceForm(request.POST or None)
    project_id = request.GET.get("project")
    if project_id:
        proj = Project.objects.filter(pk=project_id).first()
        if proj:
            form.initial.update({
                "customer": proj.customer, "project": proj,
                "invoice_type": "tax",
            })
    if form.is_valid():
        inv = form.save(commit=False)
        if request.user.company:
            inv.company = request.user.company
        if request.user.branch:
            inv.branch = request.user.branch
        inv.invoice_number = _generate_invoice_number(request.user.company,
                                                       form.cleaned_data["invoice_type"])
        inv.save()
        return redirect(reverse("billing:invoice_detail", args=[inv.pk]))
    return render(request, "billing/invoice_form.html",
                  {"form": form, "title": "New Invoice"})


@internal_required
def invoice_add_line(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    form = InvoiceLineForm(request.POST or None)
    if form.is_valid():
        line = form.save(commit=False)
        line.invoice = inv
        line.save()
        return redirect(reverse("billing:invoice_detail", args=[inv.pk]))
    return render(request, "billing/invoice_line_form.html",
                  {"form": form, "invoice": inv, "title": "Add Line"})


@internal_required
def invoice_edit(request, pk):
    """V3 improvement: allow editing invoice header fields."""
    inv = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, instance=inv)
    if form.is_valid():
        form.save()
        return redirect(reverse("billing:invoice_detail", args=[inv.pk]))
    return render(request, "billing/invoice_form.html",
                  {"form": form, "title": f"Edit – {inv.invoice_number}"})


@internal_required
def invoice_delete_line(request, pk, line_pk):
    inv = get_object_or_404(Invoice, pk=pk)
    line = get_object_or_404(InvoiceLine, pk=line_pk, invoice=inv)
    line.delete()
    return redirect(reverse("billing:invoice_detail", args=[inv.pk]))


@internal_required
def invoice_add_payment(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        pay = form.save(commit=False)
        pay.invoice = inv
        pay.received_by = request.user
        pay.save()
        # Update invoice status
        if inv.balance_due <= 0:
            inv.status = "paid"
        elif inv.amount_paid > 0:
            inv.status = "partial"
        inv.save()
        return redirect(reverse("billing:invoice_detail", args=[inv.pk]))
    return render(request, "billing/payment_form.html",
                  {"form": form, "invoice": inv, "title": "Record Payment"})


@login_required
def invoice_pdf(request, pk):
    """Allow internal users OR the linked customer to download PDF."""
    inv = get_object_or_404(Invoice, pk=pk)
    if not request.user.is_internal:
        try:
            if not (inv.customer and inv.customer.user_id == request.user.id):
                return redirect(reverse("dashboard"))
        except Exception:
            return redirect(reverse("dashboard"))
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'filename="{inv.invoice_number}.pdf"'
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             topMargin=18*mm, bottomMargin=18*mm,
                             leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TX", parent=styles["Title"], fontSize=18,
                                  textColor=colors.HexColor("#198754"))
    h_style = ParagraphStyle("HX", parent=styles["Heading2"], fontSize=12)
    center_style = ParagraphStyle("CX", parent=styles["Normal"], alignment=TA_CENTER)

    elems = []
    elems.append(Paragraph("TAX INVOICE", title_style))
    elems.append(HRFlowable(width="100%", thickness=1.2,
                            color=colors.HexColor("#198754"), spaceAfter=6))
    company_name = inv.company.name if inv.company else "PaintWorks Platform"
    elems.append(Paragraph(f"<b>{company_name}</b>", h_style))
    if inv.company and inv.company.gstin:
        elems.append(Paragraph(f"GSTIN: {inv.company.gstin}", styles["Normal"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        f"<b>Invoice #</b> {inv.invoice_number} &nbsp;&nbsp; "
        f"<b>Date:</b> {inv.invoice_date} &nbsp;&nbsp; "
        f"<b>Due:</b> {inv.due_date or '-'} &nbsp;&nbsp; "
        f"<b>Type:</b> {inv.get_invoice_type_display()}",
        styles["Normal"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(f"<b>Bill To:</b> {inv.customer.name}", styles["Normal"]))
    elems.append(Paragraph(f"<b>Phone:</b> {inv.customer.phone} &nbsp;&nbsp; "
                            f"<b>Address:</b> {inv.customer.address}", styles["Normal"]))
    if inv.customer.gstin:
        elems.append(Paragraph(f"<b>Customer GSTIN:</b> {inv.customer.gstin}", styles["Normal"]))
    elems.append(Spacer(1, 10))

    data = [["#", "Description", "Qty", "Unit", "Rate", "Amount"]]
    for i, line in enumerate(inv.lines.all(), 1):
        data.append([str(i), line.description, f"{line.quantity}", line.unit,
                      f"₹{line.rate:,.2f}", f"₹{line.amount:,.2f}"])
    data.append(["", "", "", "", "Subtotal", f"₹{inv.subtotal:,.2f}"])
    if inv.transport_charges:
        data.append(["", "", "", "", "Transport", f"₹{inv.transport_charges:,.2f}"])
    if inv.misc_charges:
        data.append(["", "", "", "", "Misc", f"₹{inv.misc_charges:,.2f}"])
    if inv.discount:
        data.append(["", "", "", "", "Discount", f"-₹{inv.discount:,.2f}"])
    data.append(["", "", "", "", f"Taxable (GST {inv.tax_rate}%)",
                  f"₹{inv.taxable_value:,.2f}"])
    data.append(["", "", "", "", f"GST {inv.tax_rate}%", f"₹{inv.tax_amount:,.2f}"])
    data.append(["", "", "", "", "Grand Total", f"₹{inv.grand_total:,.2f}"])
    data.append(["", "", "", "", "Amount Paid", f"₹{inv.amount_paid:,.2f}"])
    data.append(["", "", "", "", "Balance Due", f"₹{inv.balance_due:,.2f}"])

    tbl = Table(data, colWidths=[10*mm, 75*mm, 18*mm, 15*mm, 30*mm, 30*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#198754")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -4),
            [colors.white, colors.HexColor("#f1f3f5")]),
    ]))
    elems.append(tbl)
    elems.append(Spacer(1, 14))
    elems.append(Paragraph(
        "This is a computer-generated invoice and is authentic without signature.",
        center_style))

    doc.build(elems)
    response.write(buf.getvalue())
    buf.close()
    return response


@internal_required
def expense_list(request):
    qs = Expense.objects.all().order_by("-incurred_on")
    return render(request, "billing/expense_list.html", {"expenses": qs})


@internal_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        e = form.save(commit=False)
        if request.user.company:
            e.company = request.user.company
        if request.user.branch:
            e.branch = request.user.branch
        e.paid_by = request.user
        e.save()
        return redirect(reverse("billing:expense_list"))
    return render(request, "billing/expense_form.html",
                  {"form": form, "title": "Add Expense"})


@internal_required
def profitability_report(request):
    """Project-wise estimated vs actual cost & margin."""
    from billing.models import Expense
    from workforce.models import WorkerPayment
    projects = Project.objects.all().order_by("-created_at")
    rows = []
    for p in projects:
        revenue = Decimal(str(p.final_amount))
        material_cost = sum(
            (Decimal(str(i.quantity)) * Decimal(str(i.material.purchase_price))
             for i in p.material_issues.all()),
            Decimal("0")
        )
        labour_cost = sum(
            (Decimal(str(payment.amount))
             for w in p.worker_assignments.all()
             for payment in WorkerPayment.objects.filter(worker=w.worker, project=p)),
            Decimal("0")
        )
        expense_cost = sum(
            (Decimal(str(e.amount)) for e in Expense.objects.filter(project=p)),
            Decimal("0")
        )
        actual_cost = material_cost + labour_cost + expense_cost
        margin = revenue - actual_cost
        margin_pct = (margin / revenue * 100) if revenue else 0
        rows.append({
            "project": p, "revenue": revenue,
            "material_cost": material_cost, "labour_cost": labour_cost,
            "expense_cost": expense_cost, "actual_cost": actual_cost,
            "margin": margin, "margin_pct": round(margin_pct, 2),
        })
    return render(request, "billing/profitability.html", {"rows": rows})


@login_required
def my_invoices(request):
    """Customer-facing invoice list."""
    try:
        cust = request.user.customer_profile
    except Exception:
        return redirect(reverse("dashboard"))
    invoices = cust.invoices.all().order_by("-created_at")
    return render(request, "billing/my_invoices.html", {"invoices": invoices})
