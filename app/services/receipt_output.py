"""Receipt text formatting and printer/file hooks."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from xml.sax.saxutils import escape

from app.config import CURRENCY_SYMBOL, RECEIPT_PRINT_COMMAND
from app.services.shop_context import receipts_dir
from app.services.shop_settings import ShopSettings, get_display_shop_name


def _money(amount: float) -> str:
    return f"{CURRENCY_SYMBOL} {float(amount):,.2f}"


def format_receipt_plaintext(
    sale: dict,
    *,
    shop_name: str | None = None,
    include_shop_banner: bool = True,
) -> str:
    name = shop_name if shop_name is not None else get_display_shop_name()
    lines: list[str] = []
    if include_shop_banner:
        lines.extend([name.center(40), "=" * 40])
    lines.extend(
        [
            f"Invoice: {sale.get('invoice_number', '')}",
            f"Date: {sale.get('sale_date', '')}",
            "",
            "Items:",
        ]
    )
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
    gross_total: float,
    cash_total: float,
) -> str:
    """Receipt-style text for aggregated sales over an inclusive date range (not one invoice)."""
    name = shop_name if shop_name is not None else get_display_shop_name()
    lines: list[str] = [
        name.center(40),
        "=" * 40,
        "PERIOD SUMMARY",
        "",
        f"From: {start_date}",
        f"To:   {end_date}",
        "",
        f"Invoices: {invoice_count}",
        "",
        f"Subtotal (sum): {_money(float(subtotal_sum))}",
        f"Discounts (sum): {_money(float(discount_sum))}",
        f"Total (gross): {_money(float(gross_total))}",
        "",
        f"CASH in period: {_money(float(cash_total))}",
        "",
        "— End of summary —",
    ]
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
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, str(e)


def run_custom_receipt_command(sale: dict) -> tuple[bool, str]:
    """If ``RECEIPT_PRINT_COMMAND`` is set, run it with receipt text on stdin."""
    cmd = (RECEIPT_PRINT_COMMAND or "").strip()
    if not cmd:
        return False, "RECEIPT_PRINT_COMMAND is not set."
    text = format_receipt_plaintext(sale)
    try:
        subprocess.run(
            cmd,
            shell=True,
            input=text.encode("utf-8"),
            timeout=120,
            check=False,
        )
        return True, f"Executed: {cmd}"
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def archive_receipt_file(sale: dict) -> tuple[bool, str]:
    """Save a PDF receipt (with logo when set) under the active shop's receipts folder; falls back to .txt."""
    inv = str(sale.get("invoice_number") or "receipt").replace("/", "-")
    base = receipts_dir()
    pdf_path = base / f"{inv}.pdf"
    try:
        build_receipt_pdf(sale, pdf_path)
        return True, str(pdf_path.resolve())
    except Exception:
        txt_path = base / f"{inv}.txt"
        try:
            txt_path.write_text(format_receipt_plaintext(sale), encoding="utf-8")
            return True, str(txt_path.resolve())
        except OSError as e:
            return False, str(e)


def print_receipt(sale: dict) -> tuple[bool, str]:
    """Custom command if configured; otherwise OS print hook."""
    if (RECEIPT_PRINT_COMMAND or "").strip():
        return run_custom_receipt_command(sale)
    return send_receipt_to_system_print(sale)
