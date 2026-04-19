"""Receipt text formatting and printer/file hooks."""

from __future__ import annotations

import os
import re
import shlex
import textwrap
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from xml.sax.saxutils import escape

from app.config import CURRENCY_SYMBOL
from app.services.app_logging import log_exception
from app.services.app_settings import AppSettings
from app.services.shop_context import receipts_dir
from app.ui.date_display import format_iso_date_as_display, format_iso_datetime_for_display
from app.services.shop_settings import ShopSettings, get_display_shop_name


_UNSAFE_SHELL_CHARS = re.compile(r"[;&|`$><\r\n]")


def _effective_receipt_print_command() -> str:
    return AppSettings().get_receipt_print_command()


def _money(amount: float) -> str:
    return f"{CURRENCY_SYMBOL} {float(amount):,.2f}"


_RECEIPT_TEXT_WIDTH = 40


def _business_contact_wrapped_lines() -> list[str]:
    """Phone, email, then address lines — each wrapped for narrow thermal receipts."""
    s = ShopSettings()
    out: list[str] = []
    for raw in (s.get_business_phone(), s.get_business_email()):
        t = raw.strip()
        if t:
            out.extend(textwrap.wrap(t, width=_RECEIPT_TEXT_WIDTH, break_long_words=True, replace_whitespace=False))
    addr = s.get_business_address().strip()
    if addr:
        for seg in addr.splitlines():
            seg = seg.strip()
            if seg:
                out.extend(
                    textwrap.wrap(seg, width=_RECEIPT_TEXT_WIDTH, break_long_words=True, replace_whitespace=False)
                )
    return out


def _parse_custom_print_command(raw: str) -> list[str] | None:
    cmd = (raw or "").strip()
    if not cmd:
        return None
    if _UNSAFE_SHELL_CHARS.search(cmd):
        raise ValueError("Print command contains unsafe shell metacharacters.")
    parts = shlex.split(cmd, posix=(sys.platform != "win32"))
    if not parts:
        raise ValueError("Print command is empty.")
    return parts


def _run_custom_receipt_command_with_text(text: str) -> tuple[bool, str]:
    try:
        args = _parse_custom_print_command(_effective_receipt_print_command())
    except ValueError as e:
        return False, str(e)
    if not args:
        return False, "Custom print command is not set."
    try:
        subprocess.run(
            args,
            shell=False,
            input=text.encode("utf-8"),
            timeout=120,
            check=False,
        )
        return True, f"Executed: {' '.join(args)}"
    except (OSError, subprocess.TimeoutExpired) as e:
        log_exception("Custom receipt command failed", error=str(e))
        return False, str(e)


def format_receipt_plaintext(
    sale: dict,
    *,
    shop_name: str | None = None,
    include_shop_banner: bool = True,
) -> str:
    name = shop_name if shop_name is not None else get_display_shop_name()
    lines: list[str] = []
    if include_shop_banner:
        lines.extend([name.center(_RECEIPT_TEXT_WIDTH), "=" * _RECEIPT_TEXT_WIDTH])
        contact = _business_contact_wrapped_lines()
        if contact:
            lines.extend([ln.center(_RECEIPT_TEXT_WIDTH) for ln in contact])
            lines.append("")
    raw_dt = str(sale.get("sale_date") or "").strip()
    date_line = format_iso_datetime_for_display(raw_dt) if raw_dt else ""
    lines.extend(
        [
            f"Invoice: {sale.get('invoice_number', '')}",
            f"Date: {date_line}",
        ]
    )
    staff = (sale.get("cashier_name") or "").strip()
    if staff:
        lines.append(f"Served by: {staff}")
    lines.extend(["", "Items:"])
    for it in sale.get("items") or []:
        nm = (it.get("name") or "").strip() or "Item"
        cd = (it.get("code") or "").strip()
        qty = it.get("quantity", 0)
        total = float(it.get("total", 0))
        if cd:
            lines.append(f"  {nm}  ({cd})")
        else:
            lines.append(f"  {nm}")
        lines.append(f"    x{qty}  {_money(total)}")
    lines.extend(
        [
            "",
            f"Subtotal: {_money(float(sale.get('subtotal', 0)))}",
            f"Discount: {_money(float(sale.get('discount_amount', 0)))}",
            f"Total: {_money(float(sale.get('total_amount', 0)))}",
        ]
    )
    refund_total = float(sale.get("refund_total") or 0)
    if refund_total > 1e-9:
        lines.append(f"Refunded to date: {_money(refund_total)}")
        orig = float(sale.get("total_amount") or 0)
        net_after = round(orig - refund_total, 2)
        lines.append(f"Net after refunds: {_money(net_after)}")
        memos = sale.get("refund_memos") or []
        if memos:
            lines.append("Credit memos:")
            for m in memos:
                cn = (m.get("credit_memo_number") or "").strip() or "—"
                ta = float(m.get("total_refund_amount") or 0)
                lines.append(f"  {cn}  {_money(ta)}")
    lines.extend(
        [
            "",
            f"Payment: {sale.get('payment_method', '')}",
            "",
            "Thank you.",
        ]
    )
    return "\n".join(lines)


def format_period_sales_summary(
    *,
    shop_name: str | None = None,
    start_date: str,
    end_date: str,
    invoice_count: int,
    subtotal_sum: float,
    discount_sum: float,
    sales_total: float,
    refund_total: float,
    net_total: float,
    cash_total: float,
) -> str:
    """Receipt-style text for aggregated sales over an inclusive date range (not one invoice)."""
    name = shop_name if shop_name is not None else get_display_shop_name()
    s_disp = format_iso_date_as_display(str(start_date or "")[:10])
    e_disp = format_iso_date_as_display(str(end_date or "")[:10])
    lines: list[str] = [
        name.center(_RECEIPT_TEXT_WIDTH),
        "=" * _RECEIPT_TEXT_WIDTH,
    ]
    contact = _business_contact_wrapped_lines()
    if contact:
        lines.extend([ln.center(_RECEIPT_TEXT_WIDTH) for ln in contact])
        lines.append("")
    lines.extend(
        [
            "PERIOD SUMMARY",
            "",
            f"From: {s_disp}",
            f"To:   {e_disp}",
            "",
            f"Invoices: {invoice_count}",
            "",
            f"Subtotal (sum): {_money(float(subtotal_sum))}",
            f"Discounts (sum): {_money(float(discount_sum))}",
            f"Sales (invoice total): {_money(float(sales_total))}",
            f"Refunds: {_money(float(refund_total))}",
            f"Net total: {_money(float(net_total))}",
            "",
            f"CASH (net in period): {_money(float(cash_total))}",
            "",
            "— End of summary —",
        ]
    )
    return "\n".join(lines)


def format_credit_memo_plaintext(
    memo: dict,
    *,
    shop_name: str | None = None,
    include_shop_banner: bool = True,
) -> str:
    """Plain text for a return / credit memo (references original invoice)."""
    name = shop_name if shop_name is not None else get_display_shop_name()
    lines: list[str] = []
    if include_shop_banner:
        lines.extend([name.center(_RECEIPT_TEXT_WIDTH), "=" * _RECEIPT_TEXT_WIDTH])
        contact = _business_contact_wrapped_lines()
        if contact:
            lines.extend([ln.center(_RECEIPT_TEXT_WIDTH) for ln in contact])
            lines.append("")
    raw_dt = str(memo.get("return_date") or "").strip()
    date_line = format_iso_datetime_for_display(raw_dt) if raw_dt else ""
    lines.extend(
        [
            "CREDIT MEMO / REFUND",
            "",
            f"Credit memo: {memo.get('credit_memo_number', '')}",
            f"Date: {date_line}",
            f"Original invoice: {memo.get('original_invoice_number', '')}",
        ]
    )
    odt = str(memo.get("original_sale_date") or "").strip()
    if odt:
        lines.append(f"Original sale: {format_iso_datetime_for_display(odt)}")
    staff = (memo.get("cashier_name") or "").strip()
    if staff:
        lines.append(f"Processed by: {staff}")
    lines.extend(["", "Returned items:"])
    for it in memo.get("items") or []:
        nm = (it.get("name") or "").strip() or "Item"
        cd = (it.get("code") or "").strip()
        qty = it.get("quantity_returned", 0)
        total = float(it.get("line_refund_amount", 0))
        if cd:
            lines.append(f"  {nm}  ({cd})")
        else:
            lines.append(f"  {nm}")
        lines.append(f"    x{qty}  {_money(total)}")
    lines.extend(
        [
            "",
            f"Total refund: {_money(float(memo.get('total_refund_amount', 0)))}",
            "",
            f"Refund via: {memo.get('payment_method', '')}",
            "",
            "Thank you.",
        ]
    )
    return "\n".join(lines)


def _receipt_logo_flowable():
    """ReportLab Image for shop logo, sized for a narrow receipt, or None."""
    try:
        from PIL import Image as PILImage
        from reportlab.platypus import Image as RLImage
    except ImportError:
        return None

    path = ShopSettings().get_logo_path()
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        from reportlab.lib.units import inch

        pil = PILImage.open(p)
        w, h = pil.size
        max_w = 1.75 * inch
        max_h = 1.25 * inch
        rw = max_w
        rh = h * (rw / w)
        if rh > max_h:
            rh = max_h
            rw = w * (rh / h)
        return RLImage(str(p.resolve()), width=rw, height=rh)
    except OSError:
        return None


def build_receipt_pdf(sale: dict, dest: Path) -> None:
    """Write a PDF receipt (shop logo when set, then shop name and body)."""
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    dest.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReceiptBody",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=9,
    )

    story = []
    logo = _receipt_logo_flowable()
    if logo is not None:
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 0.15 * inch))

    shop = escape(get_display_shop_name())
    story.append(Paragraph(f'<para align="center">{shop}</para>', title_style))

    contact_lines = _business_contact_wrapped_lines()
    if contact_lines:
        contact_style = ParagraphStyle(
            "ReceiptContact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            spaceAfter=6,
        )
        chtml = "<br/>".join(escape(x) for x in contact_lines)
        story.append(Paragraph(f'<para align="center">{chtml}</para>', contact_style))
    else:
        story.append(Spacer(1, 0.08 * inch))

    body = format_receipt_plaintext(sale, include_shop_banner=False)
    story.append(Preformatted(body, body_style))

    doc = SimpleDocTemplate(
        str(dest),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Receipt {sale.get('invoice_number', '')}",
    )
    doc.build(story)


def _write_temp_receipt(text: str) -> Path:
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="receipt_", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return Path(path)


def _write_temp_receipt_pdf(sale: dict) -> Path:
    fd, path = tempfile.mkstemp(suffix=".pdf", prefix="receipt_", text=False)
    os.close(fd)
    p = Path(path)
    try:
        build_receipt_pdf(sale, p)
        return p
    except Exception:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _unlink_later(path: Path, delay_sec: float = 90.0) -> None:
    def run() -> None:
        time.sleep(delay_sec)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    threading.Thread(target=run, daemon=True).start()


def send_receipt_to_system_print(sale: dict) -> tuple[bool, str]:
    """Print PDF receipt (includes shop logo when configured). Falls back to plain text if PDF fails."""
    path: Path | None = None
    try:
        path = _write_temp_receipt_pdf(sale)
    except Exception:
        log_exception("Failed to render PDF receipt for print", invoice=sale.get("invoice_number"))
        path = None
    if path is None or not path.is_file():
        text = format_receipt_plaintext(sale)
        path = _write_temp_receipt(text)
    try:
        if sys.platform == "win32":
            os.startfile(str(path), "print")  # type: ignore[attr-defined]
            _unlink_later(path)
            return True, "Sent to the default Windows printer queue."
        for cmd in (["lpr", str(path)], ["lp", str(path)]):
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                _unlink_later(path, 30.0)
                return True, "Sent to the print queue."
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, "No print command found (install CUPS / lpr or use Save copy)."
    except OSError as e:
        log_exception("Failed system print dispatch", error=str(e))
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, str(e)


def run_custom_receipt_command(sale: dict) -> tuple[bool, str]:
    """If a custom print command is configured, run it with receipt text on stdin."""
    text = format_receipt_plaintext(sale)
    return _run_custom_receipt_command_with_text(text)


def archive_receipt_file(sale: dict) -> tuple[bool, str]:
    """Save a PDF receipt (with logo when set) under the active shop's receipts folder; falls back to .txt."""
    inv = str(sale.get("invoice_number") or "receipt").replace("/", "-")
    base = receipts_dir()
    pdf_path = base / f"{inv}.pdf"
    try:
        build_receipt_pdf(sale, pdf_path)
        return True, str(pdf_path.resolve())
    except Exception:
        log_exception("Failed to archive PDF receipt", invoice=sale.get("invoice_number"))
        txt_path = base / f"{inv}.txt"
        try:
            txt_path.write_text(format_receipt_plaintext(sale), encoding="utf-8")
            return True, str(txt_path.resolve())
        except OSError as e:
            log_exception("Failed to archive receipt text fallback", error=str(e))
            return False, str(e)


def print_receipt(sale: dict) -> tuple[bool, str]:
    """Custom command if configured; otherwise OS print hook."""
    if _effective_receipt_print_command().strip():
        return run_custom_receipt_command(sale)
    return send_receipt_to_system_print(sale)


def print_credit_memo(memo: dict) -> tuple[bool, str]:
    """Print a credit memo as plain text (same path as text receipt fallback)."""
    text = format_credit_memo_plaintext(memo)
    if _effective_receipt_print_command().strip():
        return _run_custom_receipt_command_with_text(text)
    path = _write_temp_receipt(text)
    try:
        if sys.platform == "win32":
            os.startfile(str(path), "print")  # type: ignore[attr-defined]
            _unlink_later(path)
            return True, "Sent to the default Windows printer queue."
        for cmd in (["lpr", str(path)], ["lp", str(path)]):
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                _unlink_later(path, 30.0)
                return True, "Sent to the print queue."
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, "No print command found."
    except OSError as e:
        log_exception("Failed credit memo print dispatch", error=str(e))
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, str(e)


def archive_credit_memo_file(memo: dict) -> tuple[bool, str]:
    """Save credit memo text under the shop receipts folder."""
    ref = str(memo.get("credit_memo_number") or "credit_memo").replace("/", "-")
    base = receipts_dir()
    txt_path = base / f"{ref}.txt"
    try:
        txt_path.write_text(format_credit_memo_plaintext(memo), encoding="utf-8")
        return True, str(txt_path.resolve())
    except OSError as e:
        log_exception("Failed to archive credit memo file", error=str(e))
        return False, str(e)
