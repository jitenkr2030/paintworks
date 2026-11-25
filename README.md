# PaintWorks – Whitewash, Painting & Home Improvement Management Platform

A complete Django full-stack business management platform that manages the entire home improvement
business lifecycle — from customer enquiries and site inspections to quotations, project execution,
workers, materials, billing, payments and after-service support.

**All three development versions are complete:**
- **V1 – Business MVP** (13 apps, 6 portals, complete business workflow)
- **V2 – Advanced Operations** (advanced estimation, payroll, notifications, scheduling)
- **V3 – Intelligent Platform** (AI assistant, SaaS subscriptions, PWA, advanced BI)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend   | Django 5.2 |
| Database  | SQLite (swap to PostgreSQL for production — see `settings.py`) |
| Frontend  | Django Templates + Bootstrap 5 + Bootstrap Icons |
| API       | Django REST Framework |
| PDF       | ReportLab (quotations, invoices) |
| Charts    | Chart.js |
| Auth      | Django Authentication + role-based access control |
| PWA       | manifest.json + service worker (installable, offline shell) |

## Six Connected Portals (RBAC)

| Portal | Username | Password | Purpose |
|--------|----------|----------|---------|
| Super Admin | `admin` | `admin123` | Complete platform & business control |
| Business Owner | `owner` | `owner123` | Manage company, branches & operations |
| Office Staff | `staff` | `staff123` | Enquiries, quotations, customers, billing |
| Project Manager | `pm` | `pm123` | Site inspections & project execution |
| Worker / Technician | `worker` | `worker123` | Assigned jobs, attendance, work updates |
| Customer | `cust` | `cust123` | Book services, approve quotations, track work, chat with AI |

## Module Architecture (16 Django apps)

### V1 Apps (13)
| App | Purpose |
|-----|---------|
| `accounts` | Custom User model, RBAC, Company/Branch (multi-tenant) |
| `common` | Shared mixins, dashboard router, public landing, seed command |
| `services` | Service catalogue (5 categories × ~33 subcategories) |
| `crm` | Customers, multi-property addresses, lead pipeline, follow-ups, feedback |
| `booking` | Online service booking, room-wise selection, photo uploads |
| `inspection` | Site inspection, room measurements, auto area calc (wall/ceiling/openings/net) |
| `estimation` | Quotation engine with material/labour lines, GST, PDF generation, approvals |
| `projects` | Project creation from approved quotes, work orders, tasks, daily reports, completion |
| `workforce` | Worker profiles, attendance, assignments, productivity, payments, leaves |
| `inventory` | Materials, suppliers, purchase orders, stock issues, returns, low-stock alerts |
| `billing` | GST-compliant invoices, payments, receipts, expenses, profitability, credit notes |
| `analytics` | Role-based dashboards (5) + 8 BI reports |
| `quality` | QC checklists, warranties, complaints, maintenance reminders, after-sales |

### V2 Apps & Extensions
| Feature | Description |
|---------|-------------|
| Advanced estimation engine | Paint quantity calculator using coverage rates; auto-estimate from inspection measurements |
| Worker payroll | Payroll cycles (weekly/fortnightly/monthly) auto-populated from attendance; overtime, bonus, deductions |
| Contractor settlements | Project-based or period-based settlements with work-completion % pro-rata calculation |
| Notifications | WhatsApp / SMS / Email templates with placeholders; notification log & queue |
| Project scheduling | Gantt-style timeline view per project with task bars positioned by start/duration |

### V3 Apps
| App | Purpose |
|-----|---------|
| `aiassistant` | AI customer chatbot (intent detection + rule-based replies) + AI quotation generator (rule-based, hooks ready for LLM API) |
| `subscriptions` | SaaS subscription plans (Starter/Professional/Enterprise), subscriptions, SaaS invoices, feature usage tracking |
| PWA support | `manifest.json` + service worker; installable on mobile/desktop; offline shell |
| Advanced BI | KPI dashboard, trends & forecast (12-month history + 3-month linear forecast), service popularity, photo progress intelligence |

## Complete Business Workflow

```
Customer Enquiry → Site Inspection → Measurements & Estimation →
Quotation Approval → Advance Payment → Project Creation →
Worker Assignment → Work Execution → Quality Inspection →
Final Billing → Project Completion → Warranty & After-sales →
Recurring Maintenance
```

## Quick Start

```bash
# 1. Install dependencies
pip install "Django>=5.2,<5.3" djangorestframework pillow reportlab openpyxl

# 2. Apply migrations
python manage.py migrate

# 3. Seed the demo dataset (creates company, 6 users, services, customers,
#    bookings, inspection, quotation, project, invoice, workers, inventory,
#    V2: notifications templates + payroll cycle + sample notifications,
#    V3: SaaS plans + subscription + AI quotation request + chat history)
python manage.py seed_demo

# 4. Start the dev server
python manage.py runserver

# 5. Open http://127.0.0.1:8000/ and login with any of the demo accounts above.
```

Or just run `bash start.sh` which does all of the above.

## Demo Data Highlights

- **Company:** ColourCraft Interiors (Bengaluru, GSTIN registered, Professional SaaS plan)
- **4 customers:** individual, residential society, commercial
- **4 leads** in different pipeline stages
- **1 complete demo pipeline:** Rahul Sharma's 3BHK painting project —
  booking → 4-room inspection with measurements → approved quotation
  (auto-generated material & labour lines) → in-progress project with 7 tasks
  & daily report → GST tax invoice with advance payment → warranty &
  maintenance reminder → QC checklist
- **4 workers** with attendance & payment history
- **Suppliers, materials, purchase orders** with stock levels (some low-stock)
- **V2:** 10 notification templates (WhatsApp/SMS/Email), 1 payroll cycle with
  entries, 2 notification logs
- **V3:** 3 SaaS plans (Starter ₹999, Professional ₹2999, Enterprise ₹7999),
  active Professional subscription with paid invoice, 1 AI quotation request
  (₹71,540, 85% confidence), 1 chat session with 3 messages

## All Features by Version

### V1 – Business MVP
- ✅ Customer & CRM management (multi-property, lead pipeline, follow-ups)
- ✅ Online service booking (room-wise, photos, scheduling)
- ✅ Site inspection with auto area calculation
- ✅ Quotation & estimation engine (GST, PDF, approvals, revisions)
- ✅ Project & work order management (tasks, daily reports, photos, completion)
- ✅ Worker & contractor management (attendance, assignments, payments)
- ✅ Inventory & material management (suppliers, POs, stock alerts)
- ✅ Billing, accounting & payments (GST invoices, receipts, expenses, profitability)
- ✅ Quality control & after-sales (QC checklists, warranties, complaints)
- ✅ Business dashboards & reports (5 role dashboards + 8 reports)
- ✅ Multi-company / multi-branch architecture (SaaS-ready)

### V2 – Advanced Operations
- ✅ Advanced estimation engine (paint quantity calculator, auto-estimate from inspection)
- ✅ Automated material calculations (coverage rates, coats, paint/primer/putty quantities)
- ✅ Purchase & supplier management (with goods receipt, stock auto-update)
- ✅ Detailed project scheduling (Gantt-style timeline view)
- ✅ Worker payroll (cycles auto-populated from attendance, overtime, bonus, deductions)
- ✅ Contractor settlements (work-completion % pro-rata)
- ✅ GST & financial reports (income, expenses, profit)
- ✅ Customer & worker portals (already in V1)
- ✅ WhatsApp & SMS integration (templates + notification queue & logs)

### V3 – Intelligent Platform
- ✅ AI quotation generation (rule-based engine with LLM-ready hooks; confidence scoring)
- ✅ AI customer assistant (chatbot with intent detection: greeting, booking, pricing, status, complaint, warranty, contact)
- ✅ Photo-based progress intelligence (before/during/after comparison, photo timeline)
- ✅ Advanced project profitability (revenue vs material/labour/expense with margins)
- ✅ Multi-company SaaS (subscription plans, billing cycles, feature usage tracking)
- ✅ Subscription management (Starter/Professional/Enterprise plans, SaaS invoices)
- ✅ Multi-branch operations (already in V1)
- ✅ Advanced business intelligence (KPI dashboard, trends & forecast, service popularity)
- ✅ Mobile PWA (manifest.json + service worker, installable, offline shell)

### Production Hardening & UX Improvements
- ✅ **Excel export** for all major reports (customers, leads, bookings, inspections, quotations, projects, workers, materials, invoices, sales/project/customer/worker/material/quotation reports) via OpenPyXL
- ✅ **Pagination** on all list views (15-20 per page) with reusable pagination component
- ✅ **Query optimization** with `select_related`/`prefetch_related` on heavy queries
- ✅ **Edit views** for quotations, invoices (in addition to create)
- ✅ **Customer self-service**: profile edit, online quotation approval/rejection, PDF download
- ✅ **Customer portal access control**: customers can only view their own quotations/invoices
- ✅ **Custom error pages** (404, 500, 403, 400) with branded design
- ✅ **Login attempt limiting** (5 attempts, 15-minute lockout via Django cache)
- ✅ **Production security headers** (HSTS, XSS filter, content-type nosniff, SSL redirect, secure cookies) active when DEBUG=False
- ✅ **Date-range filter** on business dashboard (filter revenue, enquiries by date range)
- ✅ **Auto-trigger notifications** when quotations are approved (WhatsApp/SMS templates)
- ✅ **Print-friendly** quotation and invoice pages (window.print() with print CSS)
- ✅ **UX improvements**: loading spinners on form submit, toast notification helper, confirm dialogs, auto-focus, card hover effects, empty states
- ✅ **CSRF trusted origins** configurable via environment variable
- ✅ **Logging** configuration (console + file)
- ✅ **Environment-based settings** for production deployment

## File Layout

```
platform/
├── homeimprovement/             # Django project settings
├── accounts/                    # User, Company, Branch, RBAC
├── common/                      # Mixins, dashboard router, seed command
├── services/                    # Service catalogue + coverage rates
├── crm/                         # Customers, properties, leads, follow-ups
├── booking/                     # Online booking & photos
├── inspection/                  # Site inspection & room measurements
├── estimation/                  # Quotation engine, paint calculator, PDF
├── projects/                    # Projects, tasks, reports, photos, timeline
├── workforce/                   # Workers, attendance, payments, payroll, settlements
├── inventory/                   # Materials, suppliers, POs, stock
├── billing/                     # Invoices, payments, expenses, profitability
├── analytics/                   # Dashboards, reports, KPI, trends, photo progress
├── quality/                     # QC, warranty, complaints, maintenance
├── notifications/               # V2: WhatsApp/SMS/Email templates & logs
├── aiassistant/                 # V3: AI chatbot + AI quotation generator
├── subscriptions/               # V3: SaaS plans, subscriptions, usage
├── templates/                   # All HTML templates (organized by app)
├── static/                      # CSS, JS, manifest.json, service worker, favicon
└── manage.py
```

## Production Notes

- **Database:** SQLite is used for portability. For production, switch `DATABASES`
  in `homeimprovement/settings.py` to PostgreSQL (commented example provided).
- **Static files:** Run `python manage.py collectstatic` before deployment.
- **Background tasks:** For V2 notifications queue processing and V3 AI features,
  add Celery + Redis in production.
- **Real AI integration:** The V3 `aiassistant` app has rule-based engines with
  hooks ready for LLM APIs. Replace `_generate_chat_reply` and
  `_generate_ai_quotation` with API calls to OpenAI / Anthropic / z-ai SDK.
- **Real WhatsApp/SMS:** Integrate with Twilio / MSG91 / Gupshup APIs in the
  `notifications` app's `send_notification` view.
- **Recommended deployment:** Ubuntu + Nginx + Gunicorn + PostgreSQL + Redis.

## Statistics
- 16 Django apps
- ~110 Python files
- ~110 HTML templates
- 6 role-based portals
- 5 service categories, 33 subcategories
- Complete end-to-end demo workflow
- All 91 tested URLs return 200 OK
