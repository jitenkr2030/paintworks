"""Reusable utilities for the platform: Excel/CSV export, pagination, helpers."""
from decimal import Decimal
from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill("solid", fgColor="0d6efd")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
THIN_BORDER = Border(
    left=Side(style="thin", color="cccccc"),
    right=Side(style="thin", color="cccccc"),
    top=Side(style="thin", color="cccccc"),
    bottom=Side(style="thin", color="cccccc"),
)


def _coerce_cell(value):
    """Convert Django model values into Excel-friendly primitives."""
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        # Excel doesn't support timezone-aware datetimes — strip tzinfo
        if isinstance(value, datetime) and value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def export_queryset_to_excel(queryset, columns, filename, sheet_name="Sheet1"):
    """Export a queryset (or list of dicts) to an Excel file.

    columns: list of (header, attr_or_callable)
        - attr can be a string attribute name (supports nested 'a.b.c')
          or a callable that takes the row
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]

    # Header row
    for col_idx, (header, _) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # Materialise queryset so we can iterate twice (column widths + data)
    items = list(queryset)

    # Data rows
    for row_idx, obj in enumerate(items, 2):
        for col_idx, (_, getter) in enumerate(columns, 1):
            if callable(getter):
                value = getter(obj)
            else:
                value = obj
                for part in getter.split("."):
                    if value is None:
                        break
                    value = getattr(value, part, "")
                    # Call if it's a bound method (e.g. get_status_display)
                    if callable(value) and not isinstance(value, (str, int, Decimal, bool, date, datetime)):
                        try:
                            value = value()
                        except TypeError:
                            break
            cell = ws.cell(row=row_idx, column=col_idx, value=_coerce_cell(value))
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # Auto column width
    for col_idx, (header, _) in enumerate(columns, 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(str(header))
        for row_idx in range(2, min(len(items) + 2, 200)):
            cell_val = ws.cell(row=row_idx, column=col_idx).value
            if cell_val is not None:
                max_len = max(max_len, len(str(cell_val)))
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 50)

    # Freeze header row
    ws.freeze_panes = "A2"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    from django.http import HttpResponse
    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    buf.close()
    return response


def export_rows_to_excel(rows, headers, filename, sheet_name="Sheet1"):
    """Export a list of dict rows to Excel.
    rows: list of dicts; headers: list of (header, key) tuples.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    for col_idx, (header, _) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER
    for row_idx, row in enumerate(rows, 2):
        for col_idx, (_, key) in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx,
                            value=_coerce_cell(row.get(key, "")))
            cell.border = THIN_BORDER
    for col_idx, (header, _) in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = min(max(len(header) + 2, 12), 40)
    ws.freeze_panes = "A2"
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    from django.http import HttpResponse
    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    buf.close()
    return response


def paginate(qs, request, per_page=20):
    """Paginate a queryset using Django's Paginator; returns the page object."""
    from django.core.paginator import Paginator
    paginator = Paginator(qs, per_page)
    page_num = request.GET.get("page", 1)
    return paginator.get_page(page_num)
