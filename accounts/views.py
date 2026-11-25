"""Accounts views: login, register, profile."""
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from .models import User, Role, Company, Branch


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )


class CustomerRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        label="Confirm Password", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "city")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_password2(self):
        if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
            raise forms.ValidationError("Passwords don't match")
        return self.cleaned_data["password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.role = Role.CUSTOMER
        user.customer_type = "individual"
        if commit:
            user.save()
        return user


class ProfileEditForm(forms.ModelForm):
    """Allow any logged-in user to update their basic profile."""
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone",
                  "city", "address", "avatar")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


def login_view(request):
    if request.user.is_authenticated:
        return redirect(reverse("dashboard"))
    form = LoginForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        # Login attempt limiting via cache
        cache_key = f"login_attempts:{username}"
        attempts = cache.get(cache_key, 0)
        limit = getattr(settings, "LOGIN_ATTEMPTS_LIMIT", 5)
        if attempts >= limit:
            timeout = getattr(settings, "LOGIN_ATTEMPTS_TIMEOUT_MINUTES", 15)
            error = (f"Too many failed login attempts. Please try again in "
                     f"{timeout} minutes.")
        else:
            user = authenticate(
                request,
                username=username,
                password=form.cleaned_data["password"],
            )
            if user and user.is_active:
                login(request, user)
                cache.delete(cache_key)
                nxt = request.GET.get("next")
                return redirect(nxt or reverse("dashboard"))
            else:
                cache.set(cache_key, attempts + 1,
                          getattr(settings, "LOGIN_ATTEMPTS_TIMEOUT_MINUTES", 15) * 60)
                remaining = limit - (attempts + 1)
                error = (f"Invalid credentials or inactive account. "
                         f"{remaining} attempt(s) remaining.")
    return render(request, "accounts/login.html", {"form": form, "error": error})


def register_view(request):
    form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("accounts:login") + "?registered=1")
    return render(request, "accounts/register.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"user": request.user})


@login_required
def profile_edit_view(request):
    """Allow users to update their own profile."""
    form = ProfileEditForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("accounts:profile"))
    return render(request, "accounts/profile_edit.html", {"form": form})
