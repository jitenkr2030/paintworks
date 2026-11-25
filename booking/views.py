"""Booking views."""
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from common.export import paginate, export_queryset_to_excel
from common.mixins import internal_required
from crm.models import Customer, Property
from services.models import ServiceSubcategory, ServiceCategory
from .models import Booking, BookingPhoto


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "preferred_date", "assigned_inspector")
    list_filter = ("status",)


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("customer", "site", "title", "property_type",
                  "rooms_description", "preferred_date", "preferred_time",
                  "services", "description", "assigned_inspector")
        widgets = {
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "preferred_time": forms.TimeInput(attrs={"type": "time"}),
            "rooms_description": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "services": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["services"].queryset = ServiceSubcategory.objects.filter(is_active=True)


class CustomerBookingForm(forms.ModelForm):
    """Form for customers to book from the public site."""
    class Meta:
        model = Booking
        fields = ("site", "title", "property_type", "rooms_description",
                  "preferred_date", "preferred_time", "services", "description")
        widgets = {
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "preferred_time": forms.TimeInput(attrs={"type": "time"}),
            "rooms_description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "property_type": forms.Select(attrs={"class": "form-select"}),
            "services": forms.CheckboxSelectMultiple,
        }


@login_required
def booking_list(request):
    status = request.GET.get("status")
    bookings = Booking.objects.all().select_related("customer", "assigned_inspector").order_by("-created_at")
    if status:
        bookings = bookings.filter(status=status)
    if request.user.is_customer:
        try:
            cust = request.user.customer_profile
            bookings = bookings.filter(customer=cust)
        except Exception:
            bookings = Booking.objects.none()
    if request.GET.get("export") == "xlsx":
        cols = [
            ("ID", "id"),
            ("Customer", lambda b: b.customer.name if b.customer else ""),
            ("Title", "title"),
            ("Preferred Date", "preferred_date"),
            ("Status", "get_status_display"),
            ("Inspector", lambda b: b.assigned_inspector.display_name if b.assigned_inspector else ""),
        ]
        return export_queryset_to_excel(bookings, cols, "bookings", "Bookings")
    page = paginate(bookings, request, per_page=20)
    return render(request, "booking/list.html",
                  {"bookings": page.object_list, "page_obj": page,
                   "statuses": Booking.Status.choices,
                   "current_status": status})


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, "booking/detail.html", {"booking": booking})


@internal_required
def booking_create(request):
    form = BookingForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        booking = form.save(commit=False)
        if request.user.company:
            booking.company = request.user.company
        if request.user.branch:
            booking.branch = request.user.branch
        booking.created_by = request.user
        booking.save()
        form.save_m2m()
        for f in request.FILES.getlist("photos"):
            BookingPhoto.objects.create(booking=booking, image=f)
        return redirect(reverse("booking:detail", args=[booking.pk]))
    return render(request, "booking/form.html", {"form": form, "title": "New Booking"})


@internal_required
def booking_edit(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    form = BookingForm(request.POST or None, request.FILES or None, instance=booking)
    if form.is_valid():
        form.save()
        for f in request.FILES.getlist("photos"):
            BookingPhoto.objects.create(booking=booking, image=f)
        return redirect(reverse("booking:detail", args=[booking.pk]))
    return render(request, "booking/form.html",
                  {"form": form, "title": f"Edit Booking #{booking.pk}",
                   "booking": booking})


@login_required
def booking_status_update(request, pk):
    if request.method == "POST":
        booking = get_object_or_404(Booking, pk=pk)
        new_status = request.POST.get("status")
        if new_status in dict(Booking.Status.choices):
            booking.status = new_status
            booking.save()
    return redirect(reverse("booking:detail", args=[pk]))


@login_required
def customer_booking_create(request):
    """A customer-facing booking form."""
    try:
        cust = request.user.customer_profile
    except Exception:
        return redirect(reverse("crm:customer_create"))
    form = CustomerBookingForm(request.POST or None)
    form.fields["services"].queryset = ServiceSubcategory.objects.filter(is_active=True)
    form.fields["site"].queryset = cust.properties.all()
    if form.is_valid():
        booking = form.save(commit=False)
        booking.customer = cust
        if request.user.company:
            booking.company = request.user.company
        booking.created_by = request.user
        booking.save()
        form.save_m2m()
        return redirect(reverse("booking:detail", args=[booking.pk]))
    return render(request, "booking/customer_form.html",
                  {"form": form, "title": "Book a Service"})
