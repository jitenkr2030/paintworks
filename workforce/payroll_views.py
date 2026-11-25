"""V2: Payroll & contractor settlement views."""
from decimal import Decimal
from datetime import timedelta
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.mixins import internal_required
from workforce.models import Worker, WorkerAttendance
from .payroll_models import PayrollCycle as PC, PayrollEntry as PE, ContractorSettlement as CS


class PayrollCycleForm(forms.ModelForm):
    class Meta:
        model = PC
        fields = ("name", "frequency", "start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class PayrollEntryForm(forms.ModelForm):
    class Meta:
        model = PE
        fields = ("worker", "present_days", "absent_days", "leave_days",
                  "overtime_hours", "base_amount", "overtime_amount",
                  "bonus", "deductions", "is_paid", "paid_on", "notes")
        widgets = {
            "paid_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class ContractorSettlementForm(forms.ModelForm):
    class Meta:
        model = CS
        fields = ("contractor", "project", "period_start", "period_end",
                  "agreed_amount", "work_completed_percent", "status",
                  "paid_on", "notes")
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "paid_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


@internal_required
def payroll_cycle_list(request):
    qs = PC.objects.all().order_by("-start_date")
    return render(request, "workforce/payroll_cycle_list.html", {"cycles": qs})


@internal_required
def payroll_cycle_create(request):
    form = PayrollCycleForm(request.POST or None)
    if form.is_valid():
        cycle = form.save(commit=False)
        if request.user.company:
            cycle.company = request.user.company
        cycle.save()
        # Auto-populate entries from attendance
        workers = Worker.objects.filter(is_active=True)
        for w in workers:
            atts = WorkerAttendance.objects.filter(
                worker=w, date__gte=cycle.start_date, date__lte=cycle.end_date)
            present = atts.filter(status="present").count()
            absent = atts.filter(status="absent").count()
            leave = atts.filter(status="leave").count()
            overtime = sum((a.hours_worked or Decimal("0")) - Decimal("8")
                           for a in atts if a.hours_worked and a.hours_worked > Decimal("8"))
            base = Decimal(str(present)) * w.wage_rate
            overtime_amount = max(Decimal("0"), overtime) * (w.wage_rate / Decimal("8")) * Decimal("1.5")
            PE.objects.create(
                cycle=cycle, worker=w,
                present_days=present, absent_days=absent, leave_days=leave,
                overtime_hours=round(overtime, 2) if overtime > 0 else Decimal("0"),
                base_amount=base, overtime_amount=overtime_amount,
            )
        return redirect(reverse("workforce:payroll_cycle_detail", args=[cycle.pk]))
    return render(request, "workforce/payroll_cycle_form.html",
                  {"form": form, "title": "New Payroll Cycle"})


@internal_required
def payroll_cycle_detail(request, pk):
    cycle = get_object_or_404(PC, pk=pk)
    entries = cycle.entries.all().select_related("worker")
    total_payable = sum((e.net_payable for e in entries), Decimal("0"))
    return render(request, "workforce/payroll_cycle_detail.html",
                  {"cycle": cycle, "entries": entries, "total_payable": total_payable})


@internal_required
def payroll_entry_edit(request, cycle_pk, entry_pk):
    entry = get_object_or_404(PE, pk=entry_pk, cycle_id=cycle_pk)
    form = PayrollEntryForm(request.POST or None, instance=entry)
    if form.is_valid():
        form.save()
        return redirect(reverse("workforce:payroll_cycle_detail", args=[cycle_pk]))
    return render(request, "workforce/payroll_entry_form.html",
                  {"form": form, "entry": entry, "title": f"Edit – {entry.worker.name}"})


@internal_required
def payroll_process_payment(request, cycle_pk, entry_pk):
    if request.method == "POST":
        entry = get_object_or_404(PE, pk=entry_pk, cycle_id=cycle_pk)
        entry.is_paid = True
        entry.paid_on = timezone.now().date()
        entry.save()
        # Create a WorkerPayment record too
        from workforce.models import WorkerPayment
        WorkerPayment.objects.create(
            worker=entry.worker, project=None,
            period_start=entry.cycle.start_date,
            period_end=entry.cycle.end_date,
            amount=entry.net_payable, paid_on=timezone.now().date(),
            method="bank", status="paid",
            notes=f"Payroll: {entry.cycle.name}",
        )
    return redirect(reverse("workforce:payroll_cycle_detail", args=[cycle_pk]))


@internal_required
def contractor_settlement_list(request):
    qs = CS.objects.all().order_by("-created_at")
    return render(request, "workforce/contractor_settlement_list.html",
                  {"items": qs})


@internal_required
def contractor_settlement_create(request):
    form = ContractorSettlementForm(request.POST or None)
    # Limit contractor choices to subcontractors
    form.fields["contractor"].queryset = Worker.objects.filter(worker_type="subcontractor")
    if form.is_valid():
        form.save()
        return redirect(reverse("workforce:contractor_settlement_list"))
    return render(request, "workforce/contractor_settlement_form.html",
                  {"form": form, "title": "New Contractor Settlement"})


@internal_required
def contractor_settlement_mark_paid(request, pk):
    if request.method == "POST":
        s = get_object_or_404(CS, pk=pk)
        s.status = "paid"
        s.paid_on = timezone.now().date()
        s.save()
    return redirect(reverse("workforce:contractor_settlement_list"))
