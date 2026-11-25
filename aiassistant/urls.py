"""AI Assistant URLs."""
from django.urls import path
from . import views

app_name = "aiassistant"

urlpatterns = [
    path("", views.ai_dashboard, name="dashboard"),
    path("chat/", views.chat_view, name="chat"),
    path("quotations/", views.ai_quotation_requests, name="quotation_requests"),
    path("quotations/new/", views.ai_quotation_create, name="quotation_create"),
    path("quotations/<int:pk>/generate/", views.ai_quotation_generate, name="ai_quotation_generate"),
    path("quotations/<int:pk>/approve/", views.ai_quotation_approve, name="ai_quotation_approve"),
]
