"""Analytics app: dashboards & BI reports."""
from datetime import timedelta
from decimal import Decimal

import json
from django.db.models import Sum, Count, Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from accounts.models import Role
from common.export import export_queryset_to_excel, export_rows_to_excel
from crm.models import Customer, Lead
from booking.models import Booking
from estimation.models import Quotation
from projects.models import Project, ProjectTask
from workforce.models import Worker, WorkerAttendance
from inventory.models import Material
from billing.models import Invoice, PaymentReceipt, Expense
from quality.models import Complaint


def _month_stats():
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now, month_start


def business_dashboard(request):
    """Business owner / super admin dashboard with date-range filter."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse("accounts:login") + f"?next={request.path}")

    now, month_start = _month_stats()

    # V3 improvement: date-range filter (default = current month)
    from datetime import date as _date
    range_start_str = request.GET.get("from")
    range_end_str = request.GET.get("to")
    try:
        range_start = _date.fromisoformat(range_start_str) if range_start_str else month_start.date()
        range_end = _date.fromisoformat(range_end_str) if range_end_str else now.date()
    except ValueError:
        range_start = month_start.date()
        range_end = now.date()

    total_revenue = (PaymentReceipt.objects
                     .filter(received_on__gte=range_start,
                             received_on__lte=range_end)
                     .aggregate(t=Sum("amount"))["t"] or Decimal("0"))
    active_projects = Project.objects.filter(status="in_progress").count()
    new_enquiries = Lead.objects.filter(created_at__date__gte=range_start,
                                         created_at__date__lte=range_end).count()
    pending_payments = sum(inv.balance_due for inv in Invoice.objects.exclude(status="paid"))

    completed = Project.objects.filter(status="completed").count()
    in_progress = Project.objects.filter(status="in_progress").count()
    planned = Project.objects.filter(status="planned").count()
    total_proj = completed + in_progress + planned or 1

    # Revenue last 6 months
    months = []
    revenues = []
    for i in range(5, -1, -1):
        d = now.replace(day=1) - timedelta(days=i*30)
        m_start = d.replace(day=1)
        next_m = (m_start + timedelta(days=32)).replace(day=1)
        rev = (PaymentReceipt.objects
               .filter(received_on__gte=m_start.date(),
                       received_on__lt=next_m.date())
               .aggregate(t=Sum("amount"))["t"] or Decimal("0"))
        months.append(m_start.strftime("%b"))
        revenues.append(float(rev))

    # Recent bookings
    recent_bookings = Booking.objects.all().order_by("-created_at")[:5]
    pending_complaints = Complaint.objects.exclude(status__in=["resolved", "closed"]).count()
    low_stock = [m for m in Material.objects.all() if m.needs_reorder][:10]

    ctx = {
        "total_revenue": total_revenue,
        "active_projects": active_projects,
        "new_enquiries": new_enquiries,
        "pending_payments": pending_payments,
        "completed_pct": round(completed / total_proj * 100, 1),
        "in_progress_pct": round(in_progress / total_proj * 100, 1),
        "planned_pct": round(planned / total_proj * 100, 1),
        "completed": completed, "in_progress": in_progress, "planned": planned,
        "months": json.dumps(months), "revenues": json.dumps(revenues),
        "recent_bookings": recent_bookings,
        "pending_complaints": pending_complaints,
        "low_stock": low_stock,
        "total_customers": Customer.objects.count(),
        "total_workers": Worker.objects.count(),
        "range_start": range_start, "range_end": range_end,
    }
    return render(request, "analytics/business_dashboard.html", ctx)


def office_dashboard(request):
    """Office staff dashboard: CRM + quotations + billing focus."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse("accounts:login") + f"?next={request.path}")
    now, month_start = _month_stats()
    open_leads = Lead.objects.exclude(stage__in=["won", "lost"]).count()
    new_bookings = Booking.objects.filter(status="new").count()
    draft_quotes = Quotation.objects.filter(status="draft").count()
    sent_quotes = Quotation.objects.filter(status="sent").count()
    pending_invoices = Invoice.objects.exclude(status="paid").count()
    return render(request, "analytics/office_dashboard.html", {
        "open_leads": open_leads,
        "new_bookings": new_bookings,
        "draft_quotes": draft_quotes,
        "sent_quotes": sent_quotes,
        "pending_invoices": pending_invoices,
        "recent_leads": Lead.objects.all().order_by("-created_at")[:5],
        "recent_customers": Customer.objects.all().order_by("-created_at")[:5],
        "recent_quotes": Quotation.objects.all().order_by("-created_at")[:5],
    })


def pm_dashboard(request):
    """Project manager dashboard."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse("accounts:login") + f"?next={request.path}")
    my_projects = Project.objects.filter(project_manager=request.user)
    active = my_projects.filter(status="in_progress")
    delayed = [p for p in active if p.is_delayed]
    tasks = ProjectTask.objects.filter(project__in=my_projects, status="todo")
    in_progress_tasks = ProjectTask.objects.filter(project__in=my_projects, status="in_progress")
    return render(request, "analytics/pm_dashboard.html", {
        "active_projects": active,
        "delayed_projects": delayed,
        "todo_tasks": tasks[:10],
        "in_progress_tasks": in_progress_tasks[:10],
        "all_my_projects": my_projects,
    })


def worker_dashboard(request):
    """Worker / technician dashboard."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse("accounts:login") + f"?next={request.path}")
    my_tasks = ProjectTask.objects.filter(assigned_to=request.user).order_by("due_date")
    today = timezone.now().date()
    today_attendance = None
    try:
        wp = request.user.worker_profile
        today_attendance = WorkerAttendance.objects.filter(worker=wp, date=today).first()
    except Exception:
        wp = None
    return render(request, "analytics/worker_dashboard.html", {
        "my_tasks": my_tasks,
        "today_attendance": today_attendance,
        "worker_profile": wp,
    })


def customer_dashboard(request):
    """Customer dashboard."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse("accounts:login") + f"?next={request.path}")
    try:
        cust = request.user.customer_profile
    except Exception:
        return render(request, "analytics/customer_dashboard.html",
                       {"customer": None, "bookings": [], "quotations": [],
                        "projects": [], "invoices": []})
    bookings = cust.bookings.all().order_by("-created_at")[:5]
    quotations = cust.quotations.all().order_by("-created_at")[:5]
    projects = cust.projects.all().order_by("-created_at")[:5]
    invoices = cust.invoices.all().order_by("-created_at")[:5]
    outstanding = sum(inv.balance_due for inv in cust.invoices.exclude(status="paid"))
    return render(request, "analytics/customer_dashboard.html", {
        "customer": cust,
        "bookings": bookings, "quotations": quotations,
        "projects": projects, "invoices": invoices,
        "outstanding": outstanding,
    })


# ---------- Reports ----------
def sales_report(request):
    now, month_start = _month_stats()
    qs = Invoice.objects.all().select_related("customer", "project").order_by("-invoice_date")
    total_invoiced = sum(i.grand_total for i in qs)
    total_paid = sum(i.amount_paid for i in qs)
    total_outstanding = sum(i.balance_due for i in qs)
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Invoice #", "invoice_number"),
            ("Customer", lambda i: i.customer.name if i.customer else ""),
            ("Project", lambda i: i.project.project_number if i.project else ""),
            ("Date", "invoice_date"),
            ("Type", "get_invoice_type_display"),
            ("Status", "get_status_display"),
            ("Subtotal", "subtotal"),
            ("Tax", "tax_amount"),
            ("Grand Total", "grand_total"),
            ("Paid", "amount_paid"),
            ("Balance", "balance_due"),
        ]
        return export_queryset_to_excel(qs, cols, "sales_report", "Sales")
    return render(request, "analytics/sales_report.html", {
        "invoices": qs[:50], "total_invoiced": total_invoiced,
        "total_paid": total_paid, "total_outstanding": total_outstanding,
    })


def project_report(request):
    qs = Project.objects.all().select_related("customer", "project_manager").order_by("-created_at")
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Project #", "project_number"),
            ("Title", "title"),
            ("Customer", lambda p: p.customer.name),
            ("Manager", lambda p: p.project_manager.display_name if p.project_manager else ""),
            ("Status", "get_status_display"),
            ("Start", "start_date"),
            ("End", "end_date"),
            ("Progress %", "progress_percent"),
            ("Final Amount", "final_amount"),
        ]
        return export_queryset_to_excel(qs, cols, "project_report", "Projects")
    return render(request, "analytics/project_report.html", {"projects": qs})


def customer_report(request):
    qs = Customer.objects.all().order_by("-created_at")
    rows = []
    for c in qs:
        rows.append({
            "customer": c,
            "bookings": c.bookings.count(),
            "quotations": c.quotations.count(),
            "projects": c.projects.count(),
            "total_business": c.total_business,
        })
    if request.GET.get("export") == "xlsx":
        headers = [
            ("Name", "name"), ("Phone", "phone"), ("Email", "email"),
            ("Type", "type"), ("City", "city"),
            ("Bookings", "bookings"), ("Quotations", "quotations"),
            ("Projects", "projects"), ("Total Business", "total_business"),
        ]
        # Flatten for export
        export_data = [{
            "name": r["customer"].name, "phone": r["customer"].phone,
            "email": r["customer"].email,
            "type": r["customer"].get_customer_type_display(),
            "city": r["customer"].city,
            "bookings": r["bookings"], "quotations": r["quotations"],
            "projects": r["projects"],
            "total_business": float(r["total_business"]),
        } for r in rows]
        return export_rows_to_excel(export_data, headers, "customer_report", "Customers")
    return render(request, "analytics/customer_report.html", {"rows": rows})


def worker_report(request):
    qs = Worker.objects.all().order_by("name")
    rows = []
    for w in qs:
        att = WorkerAttendance.objects.filter(worker=w, status="present").count()
        pays = WorkerAttendance.objects.filter(worker=w).aggregate(
            t=Sum("hours_worked"))["t"] or Decimal("0")
        rows.append({"worker": w, "present_days": att, "total_hours": pays})
    if request.GET.get("export") == "xlsx":
        headers = [
            ("Name", "name"), ("Type", "type"), ("Phone", "phone"),
            ("Skills", "skills"), ("Payment Mode", "pay_mode"),
            ("Wage Rate", "wage_rate"), ("Present Days", "present_days"),
            ("Total Hours", "total_hours"),
        ]
        export_data = [{
            "name": r["worker"].name, "type": r["worker"].get_worker_type_display(),
            "phone": r["worker"].phone, "skills": r["worker"].skills,
            "pay_mode": r["worker"].get_payment_mode_display(),
            "wage_rate": float(r["worker"].wage_rate),
            "present_days": r["present_days"],
            "total_hours": float(r["total_hours"]),
        } for r in rows]
        return export_rows_to_excel(export_data, headers, "worker_report", "Workers")
    return render(request, "analytics/worker_report.html", {"rows": rows})


def material_report(request):
    qs = Material.objects.all().order_by("name")
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Name", "name"), ("Brand", "brand"), ("Category", "category"),
            ("SKU", "sku"), ("Unit", "get_unit_display"),
            ("Purchase Price", "purchase_price"),
            ("Selling Price", "selling_price"),
            ("Current Stock", "current_stock"),
            ("Minimum Stock", "minimum_stock"),
            ("Reorder Needed", lambda m: "Yes" if m.needs_reorder else "No"),
        ]
        return export_queryset_to_excel(qs, cols, "material_report", "Materials")
    return render(request, "analytics/material_report.html", {"materials": qs})


def quotation_report(request):
    approved = Quotation.objects.filter(status="approved").count()
    rejected = Quotation.objects.filter(status="rejected").count()
    pending = Quotation.objects.filter(status__in=["draft", "sent"]).count()
    qs = Quotation.objects.all().select_related("customer").order_by("-created_at")
    if request.GET.get("export") == "xlsx":
        cols = [
            ("Quote #", "quote_number"),
            ("Customer", lambda q: q.customer.name),
            ("Date", "quotation_date"),
            ("Status", "get_status_display"),
            ("Subtotal", "subtotal"),
            ("Tax", "tax_amount"),
            ("Grand Total", "grand_total"),
            ("Advance", "advance_amount"),
        ]
        return export_queryset_to_excel(qs, cols, "quotation_report", "Quotations")
    return render(request, "analytics/quotation_report.html", {
        "quotations": qs[:50],
        "approved": approved, "rejected": rejected, "pending": pending,
    })


def financial_report(request):
    from workforce.models import WorkerPayment
    now, month_start = _month_stats()
    income = (PaymentReceipt.objects
              .aggregate(t=Sum("amount"))["t"] or Decimal("0"))
    expenses = (Expense.objects.aggregate(t=Sum("amount"))["t"] or Decimal("0"))
    worker_payments = sum(
        (p.amount for p in WorkerPayment.objects.filter(status="paid")),
        Decimal("0")
    )
    profit = income - expenses - worker_payments
    return render(request, "analytics/financial_report.html", {
        "income": income, "expenses": expenses,
        "worker_payments": worker_payments,
        "profit": profit,
        "recent_payments": PaymentReceipt.objects.all().order_by("-created_at")[:20],
        "recent_expenses": Expense.objects.all().order_by("-created_at")[:20],
    })


def service_report(request):
    from services.models import ServiceCategory, ServiceSubcategory
    cats = ServiceCategory.objects.filter(is_active=True)
    rows = []
    for c in cats:
        subs = c.subcategories.filter(is_active=True)
        rows.append({"category": c, "subs": subs, "count": subs.count()})
    return render(request, "analytics/service_report.html", {"rows": rows})


# ---------- V3: Advanced Business Intelligence ----------

def trends_forecast(request):
    """V3: Revenue & booking trends with simple linear forecast."""
    from datetime import date
    from collections import defaultdict
    # 12 months history
    now = timezone.now()
    months = []
    revenues = []
    bookings_counts = []
    for i in range(11, -1, -1):
        d = now.replace(day=1) - timedelta(days=i*30)
        m_start = d.replace(day=1)
        next_m = (m_start + timedelta(days=32)).replace(day=1)
        rev = (PaymentReceipt.objects
               .filter(received_on__gte=m_start.date(),
                       received_on__lt=next_m.date())
               .aggregate(t=Sum("amount"))["t"] or Decimal("0"))
        bk = Booking.objects.filter(created_at__gte=m_start,
                                     created_at__lt=next_m).count()
        months.append(m_start.strftime("%b %Y"))
        revenues.append(float(rev))
        bookings_counts.append(bk)
    # Simple linear forecast for next 3 months
    if len(revenues) >= 3:
        avg_growth = (revenues[-1] - revenues[0]) / max(1, len(revenues) - 1)
        forecast = [revenues[-1] + avg_growth * (i + 1) for i in range(3)]
        forecast_labels = []
        for i in range(1, 4):
            d = now.replace(day=1) + timedelta(days=i*30)
            forecast_labels.append(d.strftime("%b %Y"))
    else:
        forecast, forecast_labels = [], []
    return render(request, "analytics/trends_forecast.html", {
        "months": json.dumps(months),
        "revenues": json.dumps(revenues),
        "bookings_counts": json.dumps(bookings_counts),
        "forecast_labels": json.dumps(forecast_labels),
        "forecast": json.dumps(forecast),
    })


def kpi_dashboard(request):
    """V3: Executive KPI dashboard with all business KPIs."""
    from datetime import date
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Current month KPIs
    revenue_mtd = (PaymentReceipt.objects
                    .filter(received_on__gte=month_start.date())
                    .aggregate(t=Sum("amount"))["t"] or Decimal("0"))
    revenue_last = (PaymentReceipt.objects
                     .filter(received_on__gte=last_month_start.date(),
                             received_on__lt=month_start.date())
                     .aggregate(t=Sum("amount"))["t"] or Decimal("0"))
    revenue_growth = ((revenue_mtd - revenue_last) / revenue_last * 100
                       if revenue_last else 0)

    projects_active = Project.objects.filter(status="in_progress").count()
    projects_completed = Project.objects.filter(status="completed").count()
    projects_delayed = sum(1 for p in Project.objects.filter(status="in_progress")
                            if p.is_delayed)
    on_time_rate = ((projects_completed - projects_delayed) /
                     max(1, projects_completed) * 100)

    avg_project_value = (sum((p.final_amount for p in Project.objects.all()),
                              Decimal("0")) / max(1, Project.objects.count()))

    new_customers_mtd = Customer.objects.filter(created_at__gte=month_start).count()
    repeat_customers = Customer.objects.filter(projects__gt=1).distinct().count()
    customer_retention = (repeat_customers / max(1, Customer.objects.count()) * 100)

    outstanding = sum(inv.balance_due for inv in Invoice.objects.exclude(status="paid"))
    avg_invoice_days = 15  # placeholder; could be computed

    return render(request, "analytics/kpi_dashboard.html", {
        "revenue_mtd": revenue_mtd, "revenue_growth": round(revenue_growth, 1),
        "projects_active": projects_active,
        "projects_completed": projects_completed,
        "projects_delayed": projects_delayed,
        "on_time_rate": round(on_time_rate, 1),
        "avg_project_value": avg_project_value,
        "new_customers_mtd": new_customers_mtd,
        "customer_retention": round(customer_retention, 1),
        "outstanding": outstanding,
        "total_customers": Customer.objects.count(),
        "total_workers": Worker.objects.count(),
    })


def service_popularity(request):
    """V3: Most popular and profitable services."""
    from collections import Counter
    from services.models import ServiceSubcategory
    # Count bookings per service
    service_counts = Counter()
    for b in Booking.objects.all():
        for s in b.services.all():
            service_counts[s.id] += 1
    rows = []
    for sub in ServiceSubcategory.objects.filter(is_active=True):
        rows.append({
            "service": sub, "category": sub.category.name,
            "bookings": service_counts.get(sub.id, 0),
            "default_rate": sub.default_rate,
        })
    rows.sort(key=lambda r: r["bookings"], reverse=True)
    return render(request, "analytics/service_popularity.html", {"rows": rows})


def photo_progress(request, project_pk):
    """V3: Photo-based progress intelligence — before/during/after comparison."""
    project = get_object_or_404(Project, pk=project_pk)
    before = project.photos.filter(photo_type="before").order_by("-uploaded_at")
    during = project.photos.filter(photo_type="during").order_by("-uploaded_at")
    after = project.photos.filter(photo_type="after").order_by("-uploaded_at")
    # Progress intelligence: count of photos per stage
    stages = [
        ("Before", before, "danger"),
        ("During", during, "warning"),
        ("After", after, "success"),
    ]
    # Photo timeline
    all_photos = project.photos.all().order_by("uploaded_at")
    return render(request, "analytics/photo_progress.html", {
        "project": project, "stages": stages,
        "all_photos": all_photos,
        "before_count": before.count(),
        "during_count": during.count(),
        "after_count": after.count(),
    })
