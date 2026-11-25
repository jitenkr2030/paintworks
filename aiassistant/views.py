"""V3: AI assistant views — chatbot + quotation generator (rule-based).

Each handler is a thin wrapper around a deterministic rules engine. To upgrade
to a real LLM, replace the bodies of `_generate_chat_reply` and
`_generate_ai_quotation` with API calls — the surrounding structure
(session storage, intent detection, message persistence, UI) stays the same.
"""
import uuid
from decimal import Decimal
from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from common.mixins import internal_required
from crm.models import Customer
from estimation.models import Quotation, QuotationLine
from inspection.models import SiteInspection
from services.models import ServiceSubcategory
from .models import ChatSession, ChatMessage, AIQuotationRequest


# ---------- Admin ----------
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "started_at", "is_active")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "intent", "created_at")


@admin.register(AIQuotationRequest)
class AIQuotationRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "suggested_amount",
                    "confidence_score", "created_at")


# ---------- Rule-based intent detection & reply ----------
INTENT_KEYWORDS = {
    "greeting": ["hello", "hi", "hey", "namaste", "good morning", "good evening"],
    "book_service": ["book", "schedule", "appointment", "hire", "paint", "whitewash"],
    "pricing": ["price", "cost", "rate", "quote", "quotation", "estimate", "how much"],
    "check_status": ["status", "track", "where", "progress", "when"],
    "complaint": ["complaint", "issue", "problem", "bad", "wrong", "delay"],
    "warranty": ["warranty", "guarantee"],
    "contact": ["contact", "phone", "call", "email", "address"],
    "thanks": ["thank", "thanks", "great", "ok"],
}

INTENT_REPLIES = {
    "greeting": ("Hello! I'm PaintBot, your AI painting assistant. "
                  "I can help you: book a service, get a quotation, check project status, "
                  "or file a complaint. What would you like to do?"),
    "book_service": ("I can help you book a service. Please tell me:\n"
                       "1. What service you need (painting, whitewash, waterproofing, etc.)\n"
                       "2. Your property type (flat, house, villa, office)\n"
                       "3. Approximate area in sq ft\n"
                       "4. Preferred date"),
    "pricing": ("Our typical rates:\n"
                  "• Interior painting: ₹15/sq ft\n"
                  "• Exterior painting: ₹22/sq ft\n"
                  "• Wall putty: ₹18/sq ft\n"
                  "• Primer: ₹8/sq ft\n"
                  "• False ceiling: ₹65/sq ft\n"
                  "• Waterproofing: ₹38/sq ft\n\n"
                  "For an accurate quote, please book a free site inspection. "
                  "Would you like me to schedule one?"),
    "check_status": ("To check your project status, please share your booking ID "
                       "or registered phone number. You can also view all your "
                       "projects from the customer dashboard."),
    "complaint": ("I'm sorry to hear that. Please share:\n"
                    "1. Your project number (if known)\n"
                    "2. The issue you're facing\n"
                    "3. When did you notice it?\n"
                    "Our team will respond within 24 hours."),
    "warranty": ("All our painting services come with a 12-month warranty "
                  "covering peeling and fading. If you're within the warranty "
                  "period, repairs are free. Please share your project number."),
    "contact": ("You can reach us at:\n"
                  "• Phone: +91 98765 43210\n"
                  "• Email: info@colourcraft.in\n"
                  "• Address: 12 MG Road, Indiranagar, Bengaluru 560038\n"
                  "• Working hours: Mon-Sat, 9 AM to 7 PM"),
    "thanks": ("You're welcome! Is there anything else I can help you with?"),
    "default": ("I'm not sure I understood. I can help with: booking a service, "
                  "getting a quotation, checking project status, filing a "
                  "complaint, or warranty information. Please try again."),
}


def _detect_intent(text):
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "default"


def _generate_chat_reply(user_text):
    """Rule-based reply. Replace with LLM API call in production."""
    intent = _detect_intent(user_text)
    return INTENT_REPLIES.get(intent, INTENT_REPLIES["default"]), intent


# ---------- Chat views ----------
@login_required
def chat_view(request):
    """Customer-facing AI chatbot."""
    session_key = request.session.get("chat_session_key")
    session = None
    if session_key:
        session = ChatSession.objects.filter(session_key=session_key).first()
    if not session or not session.is_active:
        session_key = uuid.uuid4().hex
        request.session["chat_session_key"] = session_key
        session = ChatSession.objects.create(
            session_key=session_key,
            user=request.user, is_active=True,
        )
        # Add greeting
        ChatMessage.objects.create(
            session=session, role="assistant",
            content=INTENT_REPLIES["greeting"], intent="greeting",
        )

    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        if user_text:
            ChatMessage.objects.create(session=session, role="user",
                                         content=user_text)
            reply, intent = _generate_chat_reply(user_text)
            ChatMessage.objects.create(
                session=session, role="assistant",
                content=reply, intent=intent,
            )
            session.last_activity = timezone.now()
            session.save()
            return redirect(reverse("aiassistant:chat"))

    messages = session.messages.all().order_by("created_at")
    return render(request, "aiassistant/chat.html",
                  {"session": session, "messages": messages})


@internal_required
def ai_quotation_requests(request):
    """List AI quotation requests."""
    qs = AIQuotationRequest.objects.all().order_by("-created_at")
    return render(request, "aiassistant/quotation_requests.html", {"items": qs})


class AIQuoteForm(forms.ModelForm):
    class Meta:
        model = AIQuotationRequest
        fields = ("customer", "inspection", "service_required",
                  "property_type", "total_area", "rooms_count", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


@internal_required
def ai_quotation_create(request):
    """Submit a request for AI quotation generation."""
    form = AIQuoteForm(request.POST or None)
    if form.is_valid():
        req = form.save(commit=False)
        req.created_by = request.user
        req.status = "pending"
        req.save()
        return redirect(reverse("aiassistant:ai_quotation_generate", args=[req.pk]))
    return render(request, "aiassistant/quotation_form.html",
                  {"form": form, "title": "AI Quotation Request"})


@internal_required
def ai_quotation_generate(request, pk):
    """V3: Generate an AI quotation from the request."""
    req = get_object_or_404(AIQuotationRequest, pk=pk)

    # --- Rule-based AI logic (replace with LLM in production) ---
    # Base rates per sq ft
    base_rates = {
        "painting": Decimal("15"),
        "whitewash": Decimal("7"),
        "waterproofing": Decimal("38"),
        "false_ceiling": Decimal("65"),
        "putty": Decimal("18"),
        "primer": Decimal("8"),
    }
    service_lower = (req.service_required or "painting").lower()
    matched_rate = Decimal("15")
    matched_service = "painting"
    for key, rate in base_rates.items():
        if key in service_lower:
            matched_rate = rate
            matched_service = key
            break

    area = req.total_area or Decimal("1000")
    rooms = req.rooms_count or 1
    # Auto-generated quote: paint + putty + primer + labour per room
    paint_cost = area * matched_rate
    putty_cost = area * Decimal("18")
    primer_cost = area * Decimal("8")
    labour_cost = Decimal("1500") * rooms
    subtotal = paint_cost + putty_cost + primer_cost + labour_cost
    transport = Decimal("1500")
    misc = Decimal("500")
    taxable = subtotal + transport + misc
    tax = taxable * Decimal("0.18")
    grand_total = taxable + tax
    advance = grand_total * Decimal("0.5")

    # Confidence score: based on data completeness
    confidence = Decimal("70")
    if req.customer: confidence += Decimal("10")
    if req.inspection: confidence += Decimal("15")
    if req.total_area: confidence += Decimal("5")

    summary = (f"Based on {area} sq ft of {matched_service} work across {rooms} room(s), "
                f"the estimated project cost is ₹{grand_total:,.2f} (incl. 18% GST). "
                f"Breakdown: Material ₹{paint_cost + putty_cost + primer_cost:,.2f}, "
                f"Labour ₹{labour_cost:,.2f}, Transport ₹{transport}, Misc ₹{misc}. "
                f"Recommended advance: ₹{advance:,.2f}.")

    # Persist AI output on the request
    req.suggested_amount = grand_total
    req.confidence_score = min(confidence, Decimal("100"))
    req.ai_summary = summary
    req.status = "generated"
    req.save()

    return render(request, "aiassistant/quotation_preview.html", {
        "req": req, "summary": summary,
        "paint_cost": paint_cost, "putty_cost": putty_cost,
        "primer_cost": primer_cost, "labour_cost": labour_cost,
        "subtotal": subtotal, "transport": transport, "misc": misc,
        "taxable": taxable, "tax": tax,
        "grand_total": grand_total, "advance": advance,
    })


@internal_required
def ai_quotation_approve(request, pk):
    """Convert an approved AI-generated quote into a real Quotation."""
    req = get_object_or_404(AIQuotationRequest, pk=pk)
    if request.method == "POST":
        from estimation.views import generate_quote_number
        quote = Quotation.objects.create(
            quote_number=generate_quote_number(req.customer and req.customer.company or None),
            customer=req.customer,
            booking=None, inspection=req.inspection,
            quotation_date=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=30),
            status="sent",
            transport_charges=Decimal("1500"), misc_charges=Decimal("500"),
            tax_rate=Decimal("18"), advance_percentage=Decimal("50"),
            created_by=request.user,
            notes=f"AI-generated quotation. Confidence: {req.confidence_score}%",
        )
        # Add lines
        area = req.total_area or Decimal("1000")
        QuotationLine.objects.create(quotation=quote,
                                      description=f"{req.service_required} – {area} sq ft",
                                      line_type="material", quantity=area,
                                      unit="sq_ft", rate=Decimal("15"))
        QuotationLine.objects.create(quotation=quote,
                                      description=f"Wall Putty – {area} sq ft",
                                      line_type="material", quantity=area,
                                      unit="sq_ft", rate=Decimal("18"))
        QuotationLine.objects.create(quotation=quote,
                                      description=f"Primer – {area} sq ft",
                                      line_type="material", quantity=area,
                                      unit="sq_ft", rate=Decimal("8"))
        QuotationLine.objects.create(quotation=quote,
                                      description=f"Labour – {req.rooms_count or 1} room(s)",
                                      line_type="labour", quantity=req.rooms_count or 1,
                                      unit="job", rate=Decimal("1500"))
        req.generated_quotation = quote
        req.status = "approved"
        req.save()
        return redirect(reverse("estimation:detail", args=[quote.pk]))
    return render(request, "aiassistant/quotation_approve.html", {"req": req})


@internal_required
def ai_dashboard(request):
    """AI features overview."""
    stats = {
        "chat_sessions": ChatSession.objects.count(),
        "chat_messages": ChatMessage.objects.count(),
        "ai_requests": AIQuotationRequest.objects.count(),
        "ai_generated": AIQuotationRequest.objects.filter(status="generated").count(),
        "ai_approved": AIQuotationRequest.objects.filter(status="approved").count(),
        "avg_confidence": (sum((r.confidence_score for r in AIQuotationRequest.objects.all()),
                                Decimal("0")) / AIQuotationRequest.objects.count()
                            if AIQuotationRequest.objects.count() else 0),
    }
    recent_chats = ChatSession.objects.all()[:5]
    recent_requests = AIQuotationRequest.objects.all()[:5]
    return render(request, "aiassistant/dashboard.html",
                  {"stats": stats, "recent_chats": recent_chats,
                   "recent_requests": recent_requests})
