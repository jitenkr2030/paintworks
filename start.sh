#!/bin/bash
# Quick start script for the PaintWorks platform
set -e
cd "$(dirname "$0")"

echo "==> Installing dependencies..."
pip install -q "Django>=5.2,<5.3" djangorestframework pillow reportlab openpyxl 2>&1 | tail -1

echo "==> Applying migrations..."
python manage.py migrate --noinput 2>&1 | tail -3

echo "==> Seeding demo data (if not already seeded)..."
python manage.py seed_demo 2>&1 | tail -10

echo ""
echo "==> Starting development server..."
echo "    Open: http://127.0.0.1:8000/"
echo "    Login: owner / owner123  (or admin/staff/pm/worker/cust with _123 passwords)"
echo ""
python manage.py runserver
