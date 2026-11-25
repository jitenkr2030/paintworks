"""V3: Subscription views."""
from decimal import Decimal
from datetime import timedelta
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.models import Company
from common.mixins import management_required
from .models import SubscriptionPlan, Subscription, SubscriptionInvoice, FeatureUsage


# ---------- Admin ----------
@admin.register(SubscriptionPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price", "annual_price",
                    "max_users", "max_branches", "is_active")
    list_filter = ("is_active",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "plan", "status", "billing_cycle",
                    "current_period_end", "auto_renew")


@admin.register(SubscriptionInvoice)
class SubInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "subscription", "amount",
                    "grand_total", "status", "issued_at")


# ---------- Forms ----------
class PlanForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = ("name", "code", "description", "monthly_price",
                  "annual_price", "max_users", "max_branches",
                  "max_projects_per_month", "features", "is_active",
                  "display_order")


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ("company", "plan", "status", "billing_cycle",
                  "started_at", "current_period_start", "current_period_end",
                  "trial_ends_at", "auto_renew", "notes")
        widgets = {
            "started_at": forms.DateInput(attrs={"type": "date"}),
            "current_period_start": forms.DateInput(attrs={"type": "date"}),
            "current_period_end": forms.DateInput(attrs={"type": "date"}),
            "trial_ends_at": forms.DateInput(attrs={"type": "date"}),
        }


# ---------- Views ----------
@management_required
def plan_list(request):
    plans = SubscriptionPlan.objects.all().order_by("display_order")
    return render(request, "subscriptions/plan_list.html", {"plans": plans})


@management_required
def plan_create(request):
    form = PlanForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(reverse("subscriptions:plan_list"))
    return render(request, "subscriptions/plan_form.html",
                  {"form": form, "title": "New Plan"})


@management_required
def plan_edit(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    form = PlanForm(request.POST or None, instance=plan)
    if form.is_valid():
        form.save()
        return redirect(reverse("subscriptions:plan_list"))
    return render(request, "subscriptions/plan_form.html",
                  {"form": form, "title": f"Edit – {plan.name}"})


@management_required
def subscription_list(request):
    qs = Subscription.objects.all().select_related("company", "plan")
    return render(request, "subscriptions/subscription_list.html",
                  {"items": qs})


@management_required
def subscription_create(request):
    form = SubscriptionForm(request.POST or None)
    if form.is_valid():
        sub = form.save(commit=False)
        # Auto-calc current_period_end based on cycle
        if not sub.current_period_end:
            if sub.billing_cycle == "annual":
                sub.current_period_end = sub.current_period_start + timedelta(days=365)
            else:
                sub.current_period_end = sub.current_period_start + timedelta(days=30)
        if not sub.trial_ends_at and sub.status == "trial":
            sub.trial_ends_at = sub.started_at + timedelta(days=14)
        sub.save()
        return redirect(reverse("subscriptions:subscription_list"))
    return render(request, "subscriptions/subscription_form.html",
                  {"form": form, "title": "New Subscription"})


@management_required
def subscription_detail(request, pk):
    sub = get_object_or_404(Subscription, pk=pk)
    invoices = sub.invoices.all().order_by("-issued_at")
    usage = sub.usage_records.all().order_by("-period_start")
    return render(request, "subscriptions/subscription_detail.html",
                  {"sub": sub, "invoices": invoices, "usage": usage})


@management_required
def subscription_invoice_create(request, sub_pk):
    sub = get_object_or_404(Subscription, pk=sub_pk)
    if request.method == "POST":
        amount = (sub.plan.annual_price if sub.billing_cycle == "annual"
                  else sub.plan.monthly_price)
        tax = amount * Decimal("0.18")
        from datetime import timedelta as _td
        period_end = (sub.current_period_end or
                      timezone.now().date() + _td(days=30))
        inv_no = f"SaaS-{timezone.now().strftime('%Y%m%d')}-{sub.pk:04d}"
        SubscriptionInvoice.objects.create(
            subscription=sub, invoice_number=inv_no,
            period_start=sub.current_period_start,
            period_end=period_end,
            amount=amount, tax_amount=tax,
            status="sent", issued_at=timezone.now(),
        )
        # Extend subscription
        sub.current_period_start = period_end
        if sub.billing_cycle == "annual":
            sub.current_period_end = period_end + _td(days=365)
        else:
            sub.current_period_end = period_end + _td(days=30)
        sub.status = "active"
        sub.save()
    return redirect(reverse("subscriptions:subscription_detail", args=[sub_pk]))


@management_required
def subscription_invoice_mark_paid(request, sub_pk, inv_pk):
    if request.method == "POST":
        inv = get_object_or_404(SubscriptionInvoice, pk=inv_pk,
                                  subscription_id=sub_pk)
        inv.status = "paid"
        inv.paid_at = timezone.now()
        inv.payment_method = request.POST.get("method", "upi")
        inv.payment_reference = request.POST.get("reference", "")
        inv.save()
    return redirect(reverse("subscriptions:subscription_detail", args=[sub_pk]))


@management_required
def subscription_cancel(request, pk):
    sub = get_object_or_404(Subscription, pk=pk)
    if request.method == "POST":
        sub.status = "cancelled"
        sub.cancelled_at = timezone.now()
        sub.auto_renew = False
        sub.save()
    return redirect(reverse("subscriptions:subscription_detail", args=[pk]))


@management_required
def usage_report(request):
    """SaaS usage report across all companies."""
    companies = Company.objects.all()
    rows = []
    for c in companies:
        sub = getattr(c, "subscription", None)
        if not sub:
            rows.append({"company": c, "sub": None, "status": "No subscription"})
            continue
        user_count = c.users.count()
        branch_count = c.branches.count()
        rows.append({
            "company": c, "sub": sub,
            "user_count": user_count, "user_limit": sub.plan.max_users,
            "branch_count": branch_count, "branch_limit": sub.plan.max_branches,
            "status": sub.status,
        })
    return render(request, "subscriptions/usage_report.html", {"rows": rows})
