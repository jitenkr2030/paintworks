"""Estimation views, calculations, PDF generator."""
from decimal import Decimal
from io import BytesIO

from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle,
                                 Spacer, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from crm.models import Customer
from inspection.models import SiteInspection
from services.models import ServiceSubcategory
from .models import Quotation, QuotationLine


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("quote_number", "customer", "status", "grand_total",
                    "quotation_date", "approved_at")
    list_filter = ("status",)


@admin.register(QuotationLine)
class QuotationLineAdmin(admin.ModelAdmin):
    list_display = ("quotation", "description", "line_type", "quantity",
                    "unit", "rate", "amount")


class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ("customer", "booking", "inspection", "quotation_date",
                  "valid_until", "notes", "terms_conditions",
                  "transport_charges", "misc_charges", "discount",
                  "tax_rate", "advance_percentage")


class QuotationLineForm(forms.ModelForm):
    class Meta:
        model = QuotationLine
        fields = ("service", "room", "description", "line_type",
                  "quantity", "unit", "rate")


# Helper – generate quotation number
def generate_quote_number(company=None):
    today = timezone.now().strftime("%Y%m%d")
    count = Quotation.objects.filter(created_at__date=timezone.now().date()).count() + 1
    prefix = (company.name[:3].upper() if company else "QT") if company else "QT"
    return f"{prefix}-{today}-{count:03d}"


def _auto_generate_lines_from_inspection(inspection):
    """Auto-generate material & labour lines from room measurements."""
    lines = []
    if not inspection:
        return lines
    rooms = inspection.room_measurements.all()
    paint_cov = 140  # sq ft per litre @ 1 coat (default)
    putty_cov = 20   # sq ft per kg
    primer_cov = 120
    for r in rooms:
        net = Decimal(str(r.net_paint_area))
        ceil = Decimal(str(r.total_ceiling_area))
        # Material
        lines.append({"room": r.room_name, "description": f"Wall putty – {r.room_name}",
                       "line_type": "material", "quantity": net,
                       "unit": "sq_ft", "rate": Decimal("18")})
        lines.append({"room": r.room_name, "description": f"Primer – {r.room_name}",
                       "line_type": "material", "quantity": net,
                       "unit": "sq_ft", "rate": Decimal("8")})
        lines.append({"room": r.room_name, "description": f"Interior painting – {r.room_name}",
                       "line_type": "material", "quantity": net,
                       "unit": "sq_ft", "rate": Decimal("15")})
        if ceil > 0:
            lines.append({"room": r.room_name, "description": f"Ceiling painting – {r.room_name}",
                           "line_type": "material", "quantity": ceil,
                           "unit": "sq_ft", "rate": Decimal("12")})
        # Labour – one entry per room
        lines.append({"room": r.room_name, "description": f"Labour & preparation – {r.room_name}",
                       "line_type": "labour", "quantity": 1,
                       "unit": "job", "rate": Decimal("1500")})
    return lines


@internal_required
def quotation_list(request):
    status = request.GET.get("status")
    qs = Quotation.objects.all().select_related("customer").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Quote #", "quote_number"),
            ("Customer", lambda q: q.customer.name if q.customer else ""),
            ("Date", "quotation_date"),
            ("Status", "get_status_display"),
            ("Grand Total", "grand_total"),
            ("Advance", "advance_amount"),
        ]
        return export_queryset_to_excel(qs, cols, "quotations", "Quotations")
    page = paginate(qs, request, per_page=20)
    return render(request, "estimation/list.html",
                  {"quotations": page.object_list, "page_obj": page,
                   "statuses": Quotation.Status.choices,
                   "current_status": status})


@login_required
def quotation_detail(request, pk):
    """Allow internal users OR the linked customer to view a quotation."""
    quote = get_object_or_404(Quotation.objects.select_related("customer", "company"), pk=pk)
    if not request.user.is_internal:
        # Must be the linked customer
        try:
            if not (quote.customer and quote.customer.user_id == request.user.id):
                return redirect(reverse("dashboard"))
        except Exception:
            return redirect(reverse("dashboard"))
    return render(request, "estimation/detail.html",
                  {"quote": quote, "is_internal": request.user.is_internal})


@internal_required
def quotation_create(request):
    form = QuotationForm(request.POST or None)
    inspection_id = request.GET.get("inspection")
    if form.is_valid():
        quote = form.save(commit=False)
        if request.user.company:
            quote.company = request.user.company
        if request.user.branch:
            quote.branch = request.user.branch
        quote.created_by = request.user
        quote.quote_number = generate_quote_number(request.user.company)
        quote.save()
        # Auto-generate lines from inspection if linked
        if quote.inspection:
            for line_data in _auto_generate_lines_from_inspection(quote.inspection):
                QuotationLine.objects.create(quotation=quote, **line_data)
        return redirect(reverse("estimation:detail", args=[quote.pk]))
    if inspection_id:
        inspection = SiteInspection.objects.filter(pk=inspection_id).first()
        if inspection and not form.is_valid():
            form.initial["inspection"] = inspection
            form.initial["customer"] = inspection.booking.customer
            form.initial["booking"] = inspection.booking
            form.initial["quotation_date"] = timezone.now().date()
    return render(request, "estimation/form.html", {"form": form, "title": "New Quotation"})


@internal_required
def quotation_add_line(request, pk):
    quote = get_object_or_404(Quotation, pk=pk)
    form = QuotationLineForm(request.POST or None)
    if form.is_valid():
        line = form.save(commit=False)
        line.quotation = quote
        line.save()
        return redirect(reverse("estimation:detail", args=[quote.pk]))
    return render(request, "estimation/line_form.html",
                  {"form": form, "quote": quote, "title": "Add Line"})


@internal_required
def quotation_edit(request, pk):
    """V3 improvement: allow editing quotation header fields."""
    quote = get_object_or_404(Quotation, pk=pk)
    form = QuotationForm(request.POST or None, instance=quote)
    if form.is_valid():
        form.save()
        return redirect(reverse("estimation:detail", args=[quote.pk]))
    return render(request, "estimation/form.html",
                  {"form": form, "title": f"Edit – {quote.quote_number}",
                   "quote": quote})


@internal_required
def quotation_delete_line(request, pk, line_pk):
    quote = get_object_or_404(Quotation, pk=pk)
    line = get_object_or_404(QuotationLine, pk=line_pk, quotation=quote)
    line.delete()
    return redirect(reverse("estimation:detail", args=[quote.pk]))


@login_required
def quotation_status_update(request, pk):
    if request.method == "POST":
        quote = get_object_or_404(Quotation, pk=pk)
        new_status = request.POST.get("status")
        if new_status in dict(Quotation.Status.choices):
            # Customers can only approve or reject; internal can set any
            allowed = ["approved", "rejected"] if request.user.is_customer else dict(Quotation.Status.choices).keys()
            if new_status in allowed:
                quote.status = new_status
                if new_status == "approved":
                    quote.approved_at = timezone.now()
                quote.save()
                # Auto-trigger notification on approval (V2)
                try:
                    from notifications.models import NotificationTemplate, NotificationLog
                    from crm.models import Customer
                    cust = quote.customer
                    tmpl = NotificationTemplate.objects.filter(purpose="quotation_approved").first()
                    if tmpl and cust:
                        body = tmpl.render({
                            "customer_name": cust.name,
                            "quote_number": quote.quote_number,
                            "company_name": quote.company.name if quote.company else "PaintWorks",
                        })
                        NotificationLog.objects.create(
                            template=tmpl, customer=cust,
                            recipient=cust.phone, channel=tmpl.channel,
                            body=body, status="sent", sent_at=timezone.now(),
                            created_by=request.user,
                        )
                except Exception:
                    pass  # notification failure should never block the workflow
    return redirect(reverse("estimation:detail", args=[pk]))


@login_required
def quotation_pdf(request, pk):
    """Allow internal users OR the linked customer to download PDF."""
    quote = get_object_or_404(Quotation, pk=pk)
    if not request.user.is_internal:
        try:
            if not (quote.customer and quote.customer.user_id == request.user.id):
                return redirect(reverse("dashboard"))
        except Exception:
            return redirect(reverse("dashboard"))
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'filename="{quote.quote_number}.pdf"'

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             topMargin=18*mm, bottomMargin=18*mm,
                             leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18,
                                  textColor=colors.HexColor("#0d6efd"))
    h_style = ParagraphStyle("HX", parent=styles["Heading2"], fontSize=12,
                              textColor=colors.HexColor("#212529"))
    right_style = ParagraphStyle("RX", parent=styles["Normal"], alignment=TA_RIGHT)
    center_style = ParagraphStyle("CX", parent=styles["Normal"], alignment=TA_CENTER)

    elems = []
    elems.append(Paragraph("QUOTATION", title_style))
    elems.append(HRFlowable(width="100%", thickness=1.2,
                            color=colors.HexColor("#0d6efd"), spaceAfter=6))
    company_name = quote.company.name if quote.company else "PaintWorks Platform"
    elems.append(Paragraph(f"<b>{company_name}</b>", h_style))
    if quote.company and quote.company.gstin:
        elems.append(Paragraph(f"GSTIN: {quote.company.gstin}", styles["Normal"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        f"<b>Quote #</b> {quote.quote_number} &nbsp;&nbsp; "
        f"<b>Date:</b> {quote.quotation_date} &nbsp;&nbsp; "
        f"<b>Valid until:</b> {quote.valid_until or '-'}",
        styles["Normal"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(f"<b>Customer:</b> {quote.customer.name}", styles["Normal"]))
    elems.append(Paragraph(f"<b>Phone:</b> {quote.customer.phone} &nbsp;&nbsp; "
                            f"<b>Address:</b> {quote.customer.address}",
                            styles["Normal"]))
    elems.append(Spacer(1, 10))

    data = [["#", "Description", "Type", "Qty", "Unit", "Rate", "Amount"]]
    for i, line in enumerate(quote.lines.all(), 1):
        data.append([
            str(i),
            Paragraph(line.description, styles["Normal"]),
            line.get_line_type_display(),
            f"{line.quantity}",
            line.unit,
            f"₹{line.rate:,.2f}",
            f"₹{line.amount:,.2f}",
        ])
    data.append(["", "", "", "", "", "Subtotal", f"₹{quote.subtotal:,.2f}"])
    if quote.transport_charges:
        data.append(["", "", "", "", "", "Transport", f"₹{quote.transport_charges:,.2f}"])
    if quote.misc_charges:
        data.append(["", "", "", "", "", "Misc", f"₹{quote.misc_charges:,.2f}"])
    if quote.discount:
        data.append(["", "", "", "", "", "Discount", f"-₹{quote.discount:,.2f}"])
    data.append(["", "", "", "", "", f"Taxable (GST {quote.tax_rate}%)",
                  f"₹{quote.taxable_value:,.2f}"])
    data.append(["", "", "", "", "", f"GST {quote.tax_rate}%",
                  f"₹{quote.tax_amount:,.2f}"])
    data.append(["", "", "", "", "", "Grand Total",
                  f"₹{quote.grand_total:,.2f}"])

    tbl = Table(data, colWidths=[10*mm, 60*mm, 18*mm, 18*mm, 15*mm, 25*mm, 25*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -3),
            [colors.white, colors.HexColor("#f1f3f5")]),
    ]))
    elems.append(tbl)
    elems.append(Spacer(1, 10))
    elems.append(Paragraph(
        f"<b>Advance ({quote.advance_percentage}%):</b> ₹{quote.advance_amount:,.2f} &nbsp;&nbsp;"
        f"<b>Balance:</b> ₹{quote.balance_amount:,.2f}",
        styles["Normal"]))
    elems.append(Spacer(1, 10))
    if quote.terms_conditions:
        elems.append(Paragraph("<b>Terms &amp; Conditions</b>", h_style))
        for line in quote.terms_conditions.splitlines():
            if line.strip():
                elems.append(Paragraph(line, styles["Normal"]))
    elems.append(Spacer(1, 14))
    elems.append(Paragraph(
        "This is a system-generated quotation and is valid for the period mentioned above.",
        center_style))

    doc.build(elems)
    pdf = buf.getvalue()
    buf.close()
    response.write(pdf)
    return response


# ---------- V2: Advanced Estimation Engine ----------

class PaintCalculatorForm(forms.Form):
    area = forms.DecimalField(
        label="Net Paint Area (sq ft)",
        min_value=Decimal("0.01"),
        initial=Decimal("1000"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    coats = forms.IntegerField(
        label="Number of Coats", min_value=1, max_value=5, initial=2,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    coverage_per_litre = forms.DecimalField(
        label="Paint Coverage (sq ft per litre, single coat)",
        initial=Decimal("140"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Typical emulsion: 140 sq ft/L per coat.",
    )
    putty_coverage = forms.DecimalField(
        label="Putty Coverage (sq ft per kg)",
        initial=Decimal("20"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    primer_coverage = forms.DecimalField(
        label="Primer Coverage (sq ft per litre)",
        initial=Decimal("120"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )


@internal_required
def paint_calculator(request):
    """V2: Paint quantity calculator using configurable coverage rates."""
    form = PaintCalculatorForm(request.POST or None)
    result = None
    if form.is_valid():
        area = form.cleaned_data["area"]
        coats = form.cleaned_data["coats"]
        paint_cov = form.cleaned_data["coverage_per_litre"]
        putty_cov = form.cleaned_data["putty_coverage"]
        primer_cov = form.cleaned_data["primer_coverage"]

        paint_litres = (area * coats) / paint_cov
        primer_litres = area / primer_cov
        putty_kg = (area * 2) / putty_cov  # 2 coats of putty typical

        result = {
            "area": area, "coats": coats,
            "paint_litres": round(paint_litres, 2),
            "paint_4l_cans": int(Decimal(str(paint_litres)).quantize(Decimal("1")) / Decimal("4")) + 1,
            "primer_litres": round(primer_litres, 2),
            "putty_kg": round(putty_kg, 2),
            "putty_25kg_bags": int(Decimal(str(putty_kg)).quantize(Decimal("1")) / Decimal("25")) + 1,
        }
    return render(request, "estimation/paint_calculator.html",
                  {"form": form, "result": result})


@internal_required
def auto_estimate_from_inspection(request, inspection_pk):
    """V2: Auto-generate a complete quotation from an inspection's measurements
    using configurable coverage rates. Returns preview JSON."""
    from inspection.models import SiteInspection
    from services.models import CoverageRate
    inspection = get_object_or_404(SiteInspection, pk=inspection_pk)
    rooms = inspection.room_measurements.all()
    # Pull coverage rates from DB (fall back to defaults)
    def _cov(name, default):
        r = CoverageRate.objects.filter(material_name__icontains=name).first()
        return r.coverage_per_unit if r else Decimal(str(default))
    putty_cov = _cov("Putty", 20)
    primer_cov = _cov("Primer", 120)
    emulsion_cov = _cov("Emulsion", 140)

    lines = []
    grand_net = Decimal("0")
    grand_ceil = Decimal("0")
    for r in rooms:
        net = Decimal(str(r.net_paint_area))
        ceil = Decimal(str(r.total_ceiling_area))
        grand_net += net
        grand_ceil += ceil
        # Material calculations
        paint_litres = (net * 2) / emulsion_cov
        primer_litres = net / primer_cov
        putty_kg = (net * 2) / putty_cov
        lines.append({
            "room": r.room_name,
            "net_area": float(net), "ceiling_area": float(ceil),
            "paint_litres": round(float(paint_litres), 2),
            "primer_litres": round(float(primer_litres), 2),
            "putty_kg": round(float(putty_kg), 2),
            "paint_cost": float(net * Decimal("15")),
            "putty_cost": float(net * Decimal("18")),
            "primer_cost": float(net * Decimal("8")),
            "ceiling_cost": float(ceil * Decimal("12")),
            "labour_cost": 1500,
            "room_total": float(net * Decimal("15") + net * Decimal("18") +
                                net * Decimal("8") + ceil * Decimal("12") +
                                Decimal("1500")),
        })

    total = sum(Decimal(str(r["room_total"])) for r in lines)
    tax_rate = Decimal("18")
    tax_amount = total * (tax_rate / Decimal("100"))
    grand_total = total + tax_amount
    advance = grand_total * Decimal("0.5")

    return render(request, "estimation/auto_estimate_preview.html", {
        "inspection": inspection, "rooms": lines,
        "total": total, "tax_amount": tax_amount,
        "grand_total": grand_total, "advance": advance,
        "grand_net": grand_net, "grand_ceil": grand_ceil,
    })
