"""Seed management command – creates the demo dataset."""
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, Company, Branch, Role
from services.models import ServiceCategory, ServiceSubcategory, CoverageRate
from crm.models import Customer, Property, Lead
from booking.models import Booking
from inspection.models import SiteInspection, RoomMeasurement
from estimation.models import Quotation, QuotationLine
from projects.models import Project, ProjectTask, DailyWorkReport
from workforce.models import Worker, WorkerAttendance, WorkerAssignment, WorkerPayment
from inventory.models import Supplier, Material, PurchaseOrder, PurchaseOrderLine, MaterialIssue
from billing.models import Invoice, InvoiceLine, PaymentReceipt, Expense
from quality.models import QualityChecklist, Warranty, Complaint, MaintenanceReminder


SERVICE_TREE = [
    ("Whitewash & Wall Finishing", "lime", [
        ("Lime Whitewash", "sq_ft", 6),
        ("Ceiling Whitewash", "sq_ft", 7),
        ("Wall Whitening & Surface Preparation", "sq_ft", 8),
        ("Primer Application", "sq_ft", 8),
        ("Putty Application", "sq_ft", 18),
        ("Plaster Work", "sq_ft", 22),
        ("Crack Filling", "rft", 12),
        ("Dampness Treatment", "sq_ft", 35),
    ]),
    ("Painting Services", "brush", [
        ("Interior Painting (Emulsion)", "sq_ft", 15),
        ("Exterior Painting", "sq_ft", 22),
        ("Enamel Painting", "sq_ft", 28),
        ("Door & Window Painting", "sq_ft", 25),
        ("Metal Painting", "sq_ft", 30),
        ("Texture Painting", "sq_ft", 45),
        ("Stencil Painting", "sq_ft", 50),
        ("Decorative Painting", "sq_ft", 65),
    ]),
    ("Kitchen & Bathroom Renovation", "house-heart", [
        ("Modular Kitchen Installation", "job", 75000),
        ("Bathroom Remodelling", "job", 45000),
        ("Plumbing & Sanitary Fittings", "job", 12000),
        ("Countertop Installation", "rft", 1500),
        ("Cabinet Work", "rft", 1200),
    ]),
    ("Interior Improvement", "columns", [
        ("False Ceiling (POP)", "sq_ft", 65),
        ("Gypsum Partition", "sq_ft", 85),
        ("Flooring (Vitrified Tile)", "sq_ft", 55),
        ("Wall Tiling", "sq_ft", 45),
        ("Carpentry & Furniture Repair", "hour", 350),
        ("Door & Window Installation", "item", 4500),
    ]),
    ("Repair & Maintenance", "wrench-adjustable", [
        ("Waterproofing", "sq_ft", 38),
        ("Roof & Terrace Repair", "sq_ft", 32),
        ("Electrical Work", "hour", 300),
        ("Plumbing Repair", "hour", 280),
        ("Deep Cleaning", "sq_ft", 4),
        ("Annual Maintenance", "job", 9000),
    ]),
]


def _make_users():
    company = Company.objects.create(
        name="ColourCraft Interiors",
        legal_name="ColourCraft Interiors Pvt Ltd",
        gstin="27ABCDE1234F1Z5",
        pan="ABCDE1234F",
        email="info@colourcraft.in",
        phone="+91 98765 43210",
        address="12 MG Road, Indiranagar",
        city="Bengaluru", state="Karnataka", pincode="560038",
    )
    branch = Branch.objects.create(
        company=company, name="Indiranagar HO", code="BLR-01",
        address="12 MG Road, Indiranagar",
        city="Bengaluru", state="Karnataka", pincode="560038",
        phone="+91 80 2345 6789",
        email="ho@colourcraft.in",
    )
    users = {}
    role_specs = [
        ("admin", "admin123", "Super Admin", Role.SUPER_ADMIN, True),
        ("owner", "owner123", "Business Owner", Role.BUSINESS_OWNER, True),
        ("staff", "staff123", "Office Staff", Role.OFFICE_STAFF, True),
        ("pm", "pm123", "Project Manager", Role.PROJECT_MANAGER, True),
        ("worker", "worker123", "Worker", Role.WORKER, True),
        ("cust", "cust123", "Customer", Role.CUSTOMER, False),
    ]
    for uname, pwd, name, role, internal in role_specs:
        fn, ln = name.split(" ", 1) if " " in name else (name, "")
        u = User.objects.create_user(
            username=uname, password=pwd,
            email=f"{uname}@colourcraft.in",
            first_name=fn, last_name=ln,
            role=role, company=company if internal else None,
            branch=branch if internal else None,
            is_staff_user=internal, phone="+91 90000 00000",
            city="Bengaluru",
        )
        users[role] = u
    return company, branch, users


def _make_services():
    for idx, (cat_name, icon, subs) in enumerate(SERVICE_TREE):
        cat = ServiceCategory.objects.create(
            code=cat_name.split()[0].lower()[:20],
            name=cat_name, icon=f"bi bi-{icon}",
            display_order=idx,
        )
        for s_name, unit, rate in subs:
            ServiceSubcategory.objects.create(
                category=cat,
                code=s_name.lower().replace(" ", "-").replace("&", "and")[:30],
                name=s_name, default_unit=unit, default_rate=Decimal(str(rate)),
                display_order=idx,
            )
    CoverageRate.objects.create(material_name="Emulsion Paint (1 coat)",
                                 coverage_per_unit=Decimal("140"), coats=2)
    CoverageRate.objects.create(material_name="Primer",
                                 coverage_per_unit=Decimal("120"), coats=1)
    CoverageRate.objects.create(material_name="Wall Putty",
                                 coverage_per_unit=Decimal("20"), coats=2)


def _make_customers(company, branch, users):
    demo = [
        ("Rahul Sharma", "individual", "+91 99876 54321", "rahul.s@gmail.com",
         "Flat 402, Prestige Apt", "Bengaluru", "Karnataka", "560001",
         "Flat", "3BHK Home", 1450, 3, 2),
        ("Anita Reddy", "individual", "+91 98123 45678", "anita.r@gmail.com",
         "12 Jayanagar 4 Block", "Bengaluru", "Karnataka", "560011",
         "House", "Independent House", 2200, 4, 3),
        ("TechPark Pvt Ltd", "commercial", "+91 80 2345 9999", "facilities@techpark.in",
         "Tower B, TechPark", "Bengaluru", "Karnataka", "560066",
         "Commercial", "Office Tower", 18000, 0, 0),
        ("Green Meadows Society", "residential", "+91 80 2222 3333", "secretary@greenmeadows.in",
         "Green Meadows Layout", "Bengaluru", "Karnataka", "560037",
         "Society", "Residential Society", 52000, 0, 0),
    ]
    customers = []
    for (name, ctype, phone, email, addr, city, state, pin, ptype, plabel, area, beds, baths) in demo:
        c = Customer.objects.create(
            company=company, branch=branch, name=name,
            customer_type=ctype, email=email, phone=phone,
            address=addr, city=city, state=state, pincode=pin,
            source="website" if ctype == "individual" else "referral",
        )
        if name == "Rahul Sharma":
            users[Role.CUSTOMER].first_name = "Rahul"
            users[Role.CUSTOMER].last_name = "Sharma"
            users[Role.CUSTOMER].save()
            c.user = users[Role.CUSTOMER]
            c.save()
        Property.objects.create(
            customer=c, label=plabel, property_type=ptype,
            address=addr, city=city, state=state, pincode=pin,
            built_up_area=Decimal(str(area)), bedrooms=beds, bathrooms=baths,
        )
        customers.append(c)
    return customers


def _make_leads(company, branch, users):
    today = timezone.now()
    lead_specs = [
        ("Sanjay Gupta", "+91 99876 11111", "Interior Painting", "new", "website", 55000),
        ("Meera Iyer", "+91 99876 22222", "Modular Kitchen", "contacted", "referral", 80000),
        ("Vikram Singh", "+91 99876 33333", "Waterproofing", "inspection", "advertisement", 35000),
        ("Priya Nair", "+91 99876 44444", "False Ceiling", "quotation", "website", 25000),
    ]
    for name, phone, service, stage, source, val in lead_specs:
        Lead.objects.create(
            company=company, branch=branch, name=name, phone=phone,
            service_required=service, stage=stage, source=source,
            estimated_value=Decimal(str(val)),
            assigned_to=users[Role.OFFICE_STAFF],
            next_followup_at=today + timedelta(days=2),
        )


def _make_full_pipeline(company, branch, customers, users):
    cust = customers[0]
    prop = cust.properties.first()
    booking = Booking.objects.create(
        company=company, branch=branch, customer=cust, site=prop,
        title="Full Home Painting", property_type="Flat",
        rooms_description="3BHK – Living, 2 Bedrooms, Kitchen, 2 Bathrooms",
        preferred_date=timezone.now().date() + timedelta(days=5),
        status="inspected", assigned_inspector=users[Role.PROJECT_MANAGER],
        created_by=users[Role.OFFICE_STAFF],
    )
    painting = ServiceSubcategory.objects.filter(name__icontains="Interior Painting").first()
    primer = ServiceSubcategory.objects.filter(name__icontains="Primer Application").first()
    putty = ServiceSubcategory.objects.filter(name__icontains="Putty Application").first()
    if painting: booking.services.add(painting)
    if primer: booking.services.add(primer)
    if putty: booking.services.add(putty)

    inspection = SiteInspection.objects.create(
        booking=booking, inspector=users[Role.PROJECT_MANAGER],
        scheduled_at=timezone.now() - timedelta(days=2),
        completed_at=timezone.now() - timedelta(days=1),
        status="completed",
        overall_condition="Walls in fair condition; minor dampness in master bedroom.",
        recommendations="Surface preparation with putty recommended. 2 coats of premium emulsion.",
        customer_approved=True, customer_approved_at=timezone.now() - timedelta(days=1),
    )
    rooms = [
        ("Living Room", 18, 12, 10, 3, 7, 1, 4, 4, 2, "Good – minor scuff marks", False, False),
        ("Master Bedroom", 14, 12, 10, 3, 7, 1, 4, 4, 1, "Dampness on west wall", True, False),
        ("Bedroom 2", 12, 10, 10, 3, 7, 1, 4, 4, 1, "Good condition", False, False),
        ("Kitchen", 10, 8, 10, 3, 7, 1, 3, 3, 1, "Oil stains near stove", False, False),
    ]
    for r in rooms:
        RoomMeasurement.objects.create(
            inspection=inspection, room_name=r[0],
            length=Decimal(str(r[1])), width=Decimal(str(r[2])), height=Decimal(str(r[3])),
            door_width=Decimal(str(r[4])), door_height=Decimal(str(r[5])), door_count=r[6],
            window_width=Decimal(str(r[7])), window_height=Decimal(str(r[8])), window_count=r[9],
            surface_condition=r[10], dampness_observed=r[11], cracks_observed=r[12])

    quote = Quotation.objects.create(
        quote_number="CC-QT-DEMO-001", company=company, branch=branch,
        customer=cust, booking=booking, inspection=inspection,
        quotation_date=timezone.now().date() - timedelta(days=1),
        valid_until=timezone.now().date() + timedelta(days=30),
        status="approved", approved_at=timezone.now() - timedelta(days=1),
        transport_charges=Decimal("1500"), misc_charges=Decimal("500"),
        tax_rate=Decimal("18"), advance_percentage=Decimal("50"),
        created_by=users[Role.OFFICE_STAFF],
        notes="Includes 1-year warranty on paint finish.",
    )
    for r in inspection.room_measurements.all():
        net = r.net_paint_area
        QuotationLine.objects.create(quotation=quote, room=r.room_name,
                                      description=f"Wall Putty – {r.room_name}",
                                      line_type="material", quantity=net,
                                      unit="sq_ft", rate=Decimal("18"))
        QuotationLine.objects.create(quotation=quote, room=r.room_name,
                                      description=f"Primer – {r.room_name}",
                                      line_type="material", quantity=net,
                                      unit="sq_ft", rate=Decimal("8"))
        QuotationLine.objects.create(quotation=quote, room=r.room_name,
                                      description=f"Interior Painting – {r.room_name}",
                                      line_type="material", quantity=net,
                                      unit="sq_ft", rate=Decimal("15"))
        ceil = r.total_ceiling_area
        QuotationLine.objects.create(quotation=quote, room=r.room_name,
                                      description=f"Ceiling Painting – {r.room_name}",
                                      line_type="material", quantity=ceil,
                                      unit="sq_ft", rate=Decimal("12"))
        QuotationLine.objects.create(quotation=quote, room=r.room_name,
                                      description=f"Labour & Preparation – {r.room_name}",
                                      line_type="labour", quantity=Decimal("1"),
                                      unit="job", rate=Decimal("1500"))

    project = Project.objects.create(
        project_number="CC-PRJ-DEMO-001", company=company, branch=branch,
        customer=cust, site=prop, quotation=quote,
        title="Full Home Painting – Rahul Sharma",
        description="Complete interior painting of 3BHK apartment.",
        status="in_progress", project_manager=users[Role.PROJECT_MANAGER],
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=10),
        actual_start=timezone.now().date(),
        progress_percent=35,
        final_amount=quote.grand_total,
        advance_received=quote.advance_amount,
    )

    tasks = [
        ("Surface preparation & putty – Living Room", "Living Room", "done"),
        ("Surface preparation & putty – Master Bedroom", "Master Bedroom", "in_progress"),
        ("Dampness treatment – Master Bedroom", "Master Bedroom", "todo"),
        ("Primer coat – Living Room", "Living Room", "in_progress"),
        ("Final painting – Living Room", "Living Room", "todo"),
        ("Putty – Bedroom 2", "Bedroom 2", "todo"),
        ("Kitchen painting", "Kitchen", "todo"),
    ]
    for i, (title, room, status) in enumerate(tasks):
        ProjectTask.objects.create(
            project=project, title=title, room=room,
            assigned_to=users[Role.WORKER],
            status=status, display_order=i,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=i+2),
            completed_at=timezone.now() if status == "done" else None,
        )

    DailyWorkReport.objects.create(
        project=project, submitted_by=users[Role.PROJECT_MANAGER],
        report_date=timezone.now().date(),
        work_done="Living room putty completed. Started primer.",
        workers_count=3, hours_worked=Decimal("24"),
        material_used="Wall putty – 40 kg, Primer – 5 litres",
        issues="Dampness in master bedroom requires treatment before painting.",
    )

    invoice = Invoice.objects.create(
        invoice_number="CC-INV-DEMO-001", company=company, branch=branch,
        customer=cust, project=project, invoice_type="tax",
        invoice_date=timezone.now().date(),
        due_date=timezone.now().date() + timedelta(days=15),
        status="partial",
        transport_charges=Decimal("1500"), misc_charges=Decimal("500"),
        tax_rate=Decimal("18"),
    )
    InvoiceLine.objects.create(invoice=invoice, description="Wall Putty – All Rooms",
                                quantity=Decimal("1100"), unit="sq_ft", rate=Decimal("18"))
    InvoiceLine.objects.create(invoice=invoice, description="Primer – All Rooms",
                                quantity=Decimal("1100"), unit="sq_ft", rate=Decimal("8"))
    InvoiceLine.objects.create(invoice=invoice, description="Interior Painting – All Rooms",
                                quantity=Decimal("1100"), unit="sq_ft", rate=Decimal("15"))
    InvoiceLine.objects.create(invoice=invoice, description="Ceiling Painting",
                                quantity=Decimal("480"), unit="sq_ft", rate=Decimal("12"))
    InvoiceLine.objects.create(invoice=invoice, description="Labour & Preparation",
                                quantity=Decimal("1"), unit="job", rate=Decimal("6000"))

    PaymentReceipt.objects.create(
        invoice=invoice, amount=quote.advance_amount,
        received_on=timezone.now().date() - timedelta(days=1),
        method="upi", reference="UPI-DEMO-001",
        received_by=users[Role.OFFICE_STAFF],
        notes="Advance payment as per quotation terms",
    )

    QualityChecklist.objects.create(
        project=project, surface_preparation_ok=True,
        paint_shade_approved=True, finish_quality_ok=False,
        material_quality_verified=True, cleanup_done=False,
        customer_inspection_done=False, overall_rating=0,
        checked_by=users[Role.PROJECT_MANAGER],
        notes="Ongoing project – partial checks completed.",
    )

    Warranty.objects.create(
        project=project, warranty_period_months=12,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=365),
        coverage="Paint peeling/fading within 12 months.",
        terms="Warranty valid only if payment terms met.",
    )

    return project


def _make_workers_and_inventory(company, branch, project, users):
    workers = []
    w_specs = [
        ("Ramesh Kumar", "painter", "daily", 600, "+91 9988776655",
         "Wall putty, primer, emulsion, texture"),
        ("Suresh Patel", "painter", "daily", 550, "+91 9988776656",
         "Exterior painting, enamel"),
        ("Anil Verma", "mason", "daily", 500, "+91 9988776657",
         "Plaster, waterproofing"),
        ("Deepak Yadav", "helper", "daily", 350, "+91 9988776658",
         "Surface preparation, cleaning"),
    ]
    for name, wtype, pay_mode, rate, phone, skills in w_specs:
        w = Worker.objects.create(
            company=company, branch=branch,
            user=users[Role.WORKER] if name == "Ramesh Kumar" else None,
            name=name, phone=phone, worker_type=wtype, skills=skills,
            payment_mode=pay_mode, wage_rate=Decimal(str(rate)),
            address="Bengaluru", city="Bengaluru",
            id_proof="Aadhaar", is_active=True,
            rating=Decimal("4.5"), joined_at=timezone.now().date() - timedelta(days=180),
        )
        workers.append(w)

    WorkerAssignment.objects.create(worker=workers[0], project=project, is_active=True)
    WorkerAssignment.objects.create(worker=workers[1], project=project, is_active=True)

    for w in workers[:2]:
        for d in range(5):
            WorkerAttendance.objects.create(
                worker=w, project=project,
                date=timezone.now().date() - timedelta(days=d),
                check_in=timezone.now() - timedelta(days=d, hours=8),
                check_out=timezone.now() - timedelta(days=d),
                hours_worked=Decimal("8"), status="present",
            )

    WorkerPayment.objects.create(
        worker=workers[0], project=project,
        period_start=timezone.now().date() - timedelta(days=7),
        period_end=timezone.now().date(),
        amount=Decimal("3000"), paid_on=timezone.now().date(),
        method="upi", status="paid",
    )

    sup1 = Supplier.objects.create(company=company,
                                    name="Asian Paints Distributor",
                                    contact_person="Manoj",
                                    phone="+91 80 1111 2222",
                                    email="sales@apdist.in",
                                    gstin="29XYZAB5678C1Z9",
                                    city="Bengaluru")
    Supplier.objects.create(company=company,
                             name="Birla White Putty Hub",
                             contact_person="Geeta",
                             phone="+91 80 3333 4444",
                             city="Bengaluru")

    m1 = Material.objects.create(company=company, branch=branch,
                                  name="Tractor Emulsion", sku="AP-TE-001",
                                  category="paint", brand="Asian Paints",
                                  unit="litre", purchase_price=Decimal("240"),
                                  selling_price=Decimal("280"),
                                  current_stock=Decimal("40"),
                                  minimum_stock=Decimal("15"))
    m2 = Material.objects.create(company=company, branch=branch,
                                  name="Wall Putty", sku="BW-WP-001",
                                  category="putty", brand="Birla White",
                                  unit="kg", purchase_price=Decimal("32"),
                                  selling_price=Decimal("38"),
                                  current_stock=Decimal("8"),
                                  minimum_stock=Decimal("20"))
    m3 = Material.objects.create(company=company, branch=branch,
                                  name="Primer", sku="AP-PR-001",
                                  category="primer", brand="Asian Paints",
                                  unit="litre", purchase_price=Decimal("180"),
                                  selling_price=Decimal("220"),
                                  current_stock=Decimal("25"),
                                  minimum_stock=Decimal("10"))
    m4 = Material.objects.create(company=company, branch=branch,
                                  name="Paint Roller 9-inch", sku="TOOL-RL-09",
                                  category="tools", brand="Stanley",
                                  unit="piece", purchase_price=Decimal("180"),
                                  selling_price=Decimal("240"),
                                  current_stock=Decimal("12"),
                                  minimum_stock=Decimal("5"))

    po = PurchaseOrder.objects.create(
        po_number="CC-PO-DEMO-001", company=company, branch=branch,
        supplier=sup1, order_date=timezone.now().date() - timedelta(days=3),
        expected_date=timezone.now().date(),
        status="received", created_by=users[Role.OFFICE_STAFF],
    )
    PurchaseOrderLine.objects.create(po=po, material=m1,
                                      quantity=Decimal("40"), rate=Decimal("240"),
                                      received_quantity=Decimal("40"))
    PurchaseOrderLine.objects.create(po=po, material=m3,
                                      quantity=Decimal("25"), rate=Decimal("180"),
                                      received_quantity=Decimal("25"))

    MaterialIssue.objects.create(project=project, material=m1,
                                  quantity=Decimal("15"),
                                  issued_by=users[Role.PROJECT_MANAGER],
                                  notes="First coat – Living Room")
    MaterialIssue.objects.create(project=project, material=m2,
                                  quantity=Decimal("40"),
                                  issued_by=users[Role.PROJECT_MANAGER])

    Expense.objects.create(company=company, branch=branch, project=project,
                            category="transport",
                            description="Material transport – supplier to site",
                            amount=Decimal("800"),
                            incurred_on=timezone.now().date(),
                            paid_by=users[Role.PROJECT_MANAGER])
    Expense.objects.create(company=company, branch=branch, project=project,
                            category="food",
                            description="Worker lunch",
                            amount=Decimal("450"),
                            incurred_on=timezone.now().date(),
                            paid_by=users[Role.PROJECT_MANAGER])

    Complaint.objects.create(
        customer=project.customer, project=project,
        subject="Minor touch-up needed in kitchen",
        description="Customer noticed uneven finish near the stove area after first coat.",
        status="open", priority="low",
        assigned_to=users[Role.PROJECT_MANAGER],
    )

    MaintenanceReminder.objects.create(
        customer=project.customer, project=project,
        service_type="Annual Painting Maintenance Check",
        next_due_date=timezone.now().date() + timedelta(days=365),
        interval_months=12,
    )

    cust2 = Customer.objects.filter(name="Anita Reddy").first()
    if cust2:
        prop2 = cust2.properties.first()
        Project.objects.create(
            project_number="CC-PRJ-DEMO-002", company=company, branch=branch,
            customer=cust2, site=prop2,
            title="Exterior Painting – Anita Reddy",
            description="Complete exterior painting of independent house.",
            status="planned", project_manager=users[Role.PROJECT_MANAGER],
            start_date=timezone.now().date() + timedelta(days=5),
            end_date=timezone.now().date() + timedelta(days=20),
            progress_percent=0, final_amount=Decimal("65000"),
            advance_received=Decimal("0"),
        )


def _make_v2_v3_demo(company, branch, users):
    """V2/V3 demo data: notifications templates, payroll, SaaS plans, AI requests."""
    from notifications.models import NotificationTemplate, NotificationLog
    from notifications.views import seed_default_templates
    from workforce.payroll_models import PayrollCycle, PayrollEntry
    from subscriptions.models import (
        SubscriptionPlan, Subscription, SubscriptionInvoice, FeatureUsage)
    from aiassistant.models import ChatSession, ChatMessage, AIQuotationRequest

    # V2: Seed default notification templates
    seed_default_templates(company)
    # Sample notification logs
    cust = company.customers.first()
    if cust:
        tmpl = NotificationTemplate.objects.filter(purpose="booking_confirmation").first()
        NotificationLog.objects.create(
            template=tmpl, customer=cust, recipient=cust.phone,
            channel="whatsapp",
            body=f"Hi {cust.name}, your booking is confirmed. – {company.name}",
            status="sent", sent_at=timezone.now() - timedelta(days=2),
        )
        tmpl2 = NotificationTemplate.objects.filter(purpose="payment_received").first()
        NotificationLog.objects.create(
            template=tmpl2, customer=cust, recipient=cust.phone,
            channel="sms",
            body=f"Dear {cust.name}, we received your payment of ₹25000. – {company.name}",
            status="delivered", sent_at=timezone.now() - timedelta(days=1),
            delivered_at=timezone.now() - timedelta(days=1),
        )

    # V2: Payroll cycle
    from workforce.models import Worker, WorkerAttendance
    cycle = PayrollCycle.objects.create(
        company=company, name=f"Payroll {timezone.now().strftime('%B %Y')}",
        frequency="monthly",
        start_date=timezone.now().date() - timedelta(days=30),
        end_date=timezone.now().date(),
    )
    for w in Worker.objects.all():
        atts = WorkerAttendance.objects.filter(
            worker=w, date__gte=cycle.start_date, date__lte=cycle.end_date)
        present = atts.filter(status="present").count()
        base = Decimal(str(present)) * w.wage_rate
        PayrollEntry.objects.create(
            cycle=cycle, worker=w,
            present_days=present, absent_days=0, leave_days=0,
            overtime_hours=Decimal("0"),
            base_amount=base, overtime_amount=Decimal("0"),
            bonus=Decimal("0") if w.worker_type != "painter" else Decimal("500"),
            deductions=Decimal("0"),
        )

    # V3: SaaS subscription plans
    starter = SubscriptionPlan.objects.create(
        name="Starter", code="starter",
        description="For individual contractors and small teams.",
        monthly_price=Decimal("999"), annual_price=Decimal("9990"),
        max_users=3, max_branches=1, max_projects_per_month=10,
        features=["CRM", "Booking", "Inspection", "Quotation", "Basic Reports"],
        display_order=1,
    )
    professional = SubscriptionPlan.objects.create(
        name="Professional", code="professional",
        description="For growing painting & renovation companies.",
        monthly_price=Decimal("2999"), annual_price=Decimal("29990"),
        max_users=15, max_branches=3, max_projects_per_month=100,
        features=["Everything in Starter", "Workforce Payroll", "Inventory",
                   "GST Billing", "Quality Control", "Notifications", "Advanced Reports"],
        display_order=2,
    )
    enterprise = SubscriptionPlan.objects.create(
        name="Enterprise", code="enterprise",
        description="For multi-branch home improvement businesses.",
        monthly_price=Decimal("7999"), annual_price=Decimal("79990"),
        max_users=100, max_branches=20, max_projects_per_month=1000,
        features=["Everything in Professional", "AI Assistant", "SaaS Multi-Company",
                   "Photo Progress Intelligence", "Forecasting", "Priority Support"],
        display_order=3,
    )
    # Subscribe the demo company to Professional plan
    sub = Subscription.objects.create(
        company=company, plan=professional, status="active",
        billing_cycle="monthly",
        started_at=timezone.now().date() - timedelta(days=60),
        current_period_start=timezone.now().date() - timedelta(days=5),
        current_period_end=timezone.now().date() + timedelta(days=25),
        auto_renew=True,
    )
    SubscriptionInvoice.objects.create(
        subscription=sub,
        invoice_number=f"SaaS-{timezone.now().strftime('%Y%m%d')}-0001",
        period_start=timezone.now().date() - timedelta(days=5),
        period_end=timezone.now().date() + timedelta(days=25),
        amount=Decimal("2999"), tax_amount=Decimal("539.82"),
        status="paid", paid_at=timezone.now() - timedelta(days=5),
        payment_method="upi", payment_reference="SAAS-DEMO-001",
    )
    FeatureUsage.objects.create(
        subscription=sub, feature="users",
        period_start=timezone.now().date() - timedelta(days=5),
        period_end=timezone.now().date() + timedelta(days=25),
        used=company.users.count(), limit=professional.max_users,
    )
    FeatureUsage.objects.create(
        subscription=sub, feature="branches",
        period_start=timezone.now().date() - timedelta(days=5),
        period_end=timezone.now().date() + timedelta(days=25),
        used=company.branches.count(), limit=professional.max_branches,
    )

    # V3: AI quotation request
    if cust:
        ai_req = AIQuotationRequest.objects.create(
            customer=cust, service_required="Interior Painting",
            property_type="Flat", total_area=Decimal("1200"),
            rooms_count=3, status="generated",
            created_by=users[Role.OFFICE_STAFF],
            ai_summary="Based on 1200 sq ft of interior painting across 3 rooms, "
                       "the estimated project cost is ₹71,540 (incl. 18% GST).",
            suggested_amount=Decimal("71540"),
            confidence_score=Decimal("85"),
        )
        # Sample chat session
        session = ChatSession.objects.create(
            customer=cust, user=users[Role.CUSTOMER],
            session_key="demo-session-001",
            summary="Customer enquiry about interior painting",
        )
        ChatMessage.objects.create(
            session=session, role="assistant",
            content="Hello! I'm PaintBot, your AI painting assistant. "
                    "I can help you: book a service, get a quotation, "
                    "check project status, or file a complaint.",
            intent="greeting",
        )
        ChatMessage.objects.create(
            session=session, role="user",
            content="I want to paint my 3BHK apartment. How much will it cost?",
        )
        ChatMessage.objects.create(
            session=session, role="assistant",
            content="Our typical rates:\n• Interior painting: ₹15/sq ft\n"
                    "• Wall putty: ₹18/sq ft\n• Primer: ₹8/sq ft\n\n"
                    "For an accurate quote, please book a free site inspection. "
                    "Would you like me to schedule one?",
            intent="pricing",
        )


class Command(BaseCommand):
    help = "Seed the platform with a complete demo dataset"

    def handle(self, *args, **kwargs):
        if User.objects.filter(username="owner").exists():
            self.stdout.write(self.style.WARNING("Seed data already exists – skipping."))
            return
        self.stdout.write("Creating company, users and branches...")
        company, branch, users = _make_users()
        self.stdout.write("Creating service catalogue...")
        _make_services()
        self.stdout.write("Creating customers...")
        customers = _make_customers(company, branch, users)
        self.stdout.write("Creating leads...")
        _make_leads(company, branch, users)
        self.stdout.write("Creating demo pipeline (booking -> inspection -> quotation -> project -> invoice)...")
        project = _make_full_pipeline(company, branch, customers, users)
        self.stdout.write("Creating workers and inventory...")
        _make_workers_and_inventory(company, branch, project, users)
        self.stdout.write("Creating V2/V3 demo data (notifications, payroll, SaaS, AI)...")
        _make_v2_v3_demo(company, branch, users)
        self.stdout.write(self.style.SUCCESS(
            "\nSeed complete.\n\n"
            "Demo logins:\n"
            "  owner / owner123    - Business Owner\n"
            "  staff / staff123    - Office Staff\n"
            "  pm / pm123          - Project Manager\n"
            "  worker / worker123  - Worker\n"
            "  cust / cust123      - Customer (linked to Rahul Sharma)\n"
            "  admin / admin123    - Super Admin\n"
        ))
