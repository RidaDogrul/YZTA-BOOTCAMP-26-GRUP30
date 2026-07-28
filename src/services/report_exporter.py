"""

Rapor Dışa Aktarma Servisi — Task S3-M3
-----------------------------------------
Bir rapor sözlüğünü (Insight Generator / ChatResponse çıktısı) PDF veya
Excel dosyasına çevirir.

TASARIM: Servis DEPOLAMADAN BAĞIMSIZ. Rapor veritabanından okunmuyor;
içerik doğrudan parametre olarak veriliyor. Böylece frontend ekrandaki
raporu olduğu gibi indirmeye gönderebilir.

Türkçe karakter notu: PDF'in varsayılan fontları (Helvetica) ş/ğ/ı/İ
karakterlerini gösteremez. Bu yüzden sistemde bulunan bir Unicode TTF
font otomatik olarak kaydedilir; bulunamazsa Helvetica'ya düşülür.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_PDF_CHART_ROWS = 30    # PDF'e sığması için tablo satır sınırı
MAX_PDF_TABLE_COLS = 6     # PDF'te gösterilecek maksimum sütun

# (normal, bold, font adı) — sırayla denenir, ilk bulunan kullanılır.
_FONT_CANDIDATES: list[tuple[str, str, str]] = [
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf", "Arial"),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans",
    ),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf", "Arial"),
]


# ---------------------------------------------------------------------------
# Rapor modeli — gelen sözlüğü tek tip hale getirir
# ---------------------------------------------------------------------------
@dataclass
class ReportDocument:
    """Dışa aktarılacak raporun normalize edilmiş hali."""

    title: str = "Analiz Raporu"
    question: str = ""
    summary: str = ""
    sql_query: str = ""
    chart_data: list[dict[str, Any]] = field(default_factory=list)
    action_plan: list[str] = field(default_factory=list)
    action_details: list[dict[str, Any]] = field(default_factory=list)
    action_reasoning: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    language: str = "tr"
    created_at: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ReportDocument":
        """ChatResponse / InsightResult sözlüğünden rapor nesnesi üretir."""
        return cls(
            title=payload.get("title") or "Analiz Raporu",
            question=payload.get("question", ""),
            summary=payload.get("summary", ""),
            sql_query=payload.get("sql_query", ""),
            chart_data=payload.get("chart_data") or [],
            action_plan=payload.get("action_plan") or [],
            action_details=payload.get("action_details") or [],
            action_reasoning=payload.get("action_reasoning", ""),
            metrics=payload.get("metrics") or {},
            language=payload.get("language", "tr"),
            created_at=payload.get("created_at")
            or datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M"),
        )

    def action_rows(self) -> list[dict[str, str]]:
        """
        Aksiyonları tek tip satırlara çevirir.
        action_details varsa onu (öncelik/gerekçe ile), yoksa düz listeyi kullanır.
        """
        if self.action_details:
            return [
                {
                    "action": str(item.get("action", "")),
                    "priority": str(item.get("priority", "")),
                    "reason": str(item.get("reason", "")),
                }
                for item in self.action_details
            ]
        return [{"action": str(a), "priority": "", "reason": ""} for a in self.action_plan]


# ---------------------------------------------------------------------------
# EXCEL
# ---------------------------------------------------------------------------
def build_excel(report: ReportDocument) -> bytes:
    """
    Raporu çok sayfalı bir Excel dosyasına çevirir:
      - Özet: rapor bilgileri ve metrikler
      - Grafik Verisi: chart_data'nın tamamı
      - Aksiyon Planı: aksiyon / öncelik / gerekçe
    """
    buffer = io.BytesIO()

    # --- Özet sayfası (anahtar-değer) ---
    summary_rows: list[dict[str, Any]] = [
        {"Alan": "Rapor", "Değer": report.title},
        {"Alan": "Tarih", "Değer": report.created_at},
        {"Alan": "Soru", "Değer": report.question},
        {"Alan": "Özet", "Değer": report.summary},
    ]
    if report.sql_query:
        summary_rows.append({"Alan": "Çalıştırılan Sorgu", "Değer": report.sql_query})
    if report.action_reasoning:
        summary_rows.append({"Alan": "Plan Gerekçesi", "Değer": report.action_reasoning})
    # Metrikleri de aynı sayfaya ekle (tahmin varsa dolu gelir).
    for key, value in report.metrics.items():
        summary_rows.append({"Alan": f"Metrik: {key}", "Değer": str(value)})

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Özet", index=False)

        if report.chart_data:
            pd.DataFrame(report.chart_data).to_excel(
                writer, sheet_name="Grafik Verisi", index=False
            )

        action_rows = report.action_rows()
        if action_rows:
            pd.DataFrame(action_rows).rename(
                columns={"action": "Aksiyon", "priority": "Öncelik", "reason": "Gerekçe"}
            ).to_excel(writer, sheet_name="Aksiyon Planı", index=False)

        _autosize_columns(writer)

    return buffer.getvalue()


def _autosize_columns(writer: Any, max_width: int = 60) -> None:
    """Sütun genişliklerini içeriğe göre ayarlar (okunabilirlik için)."""
    for worksheet in writer.book.worksheets:
        for column_cells in worksheet.columns:
            longest = max(
                (len(str(cell.value)) for cell in column_cells if cell.value is not None),
                default=10,
            )
            letter = column_cells[0].column_letter
            worksheet.column_dimensions[letter].width = min(longest + 2, max_width)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _register_unicode_font() -> tuple[str, str]:
    """
    Türkçe karakterleri destekleyen bir sistem fontu bulup kaydeder.
    Returns: (normal_font_adı, bold_font_adı)
    """
    for regular_path, bold_path, name in _FONT_CANDIDATES:
        if not Path(regular_path).exists():
            continue
        pdfmetrics.registerFont(TTFont(name, regular_path))
        bold_name = name
        if Path(bold_path).exists():
            bold_name = f"{name}-Bold"
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
        logger.info("PDF fontu kaydedildi", extra={"font": name})
        return name, bold_name

    logger.warning(
        "Unicode font bulunamadı; Helvetica kullanılacak. "
        "Türkçe karakterler hatalı görünebilir."
    )
    return "Helvetica", "Helvetica-Bold"


def build_pdf(report: ReportDocument) -> bytes:
    """Raporu tek dosyalık, okunabilir bir PDF'e çevirir."""
    font, font_bold = _register_unicode_font()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=report.title,
    )

    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle", parent=base["Title"], fontName=font_bold, fontSize=18, spaceAfter=6
    )
    heading_style = ParagraphStyle(
        "DocHeading", parent=base["Heading2"], fontName=font_bold, fontSize=13,
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1f4e79"),
    )
    body_style = ParagraphStyle(
        "DocBody", parent=base["BodyText"], fontName=font, fontSize=10.5, leading=15,
    )
    meta_style = ParagraphStyle(
        "DocMeta", parent=body_style, fontSize=9, textColor=colors.grey,
    )

    story: list[Any] = [
        Paragraph(report.title, title_style),
        Paragraph(f"Oluşturulma: {report.created_at}", meta_style),
    ]
    if report.question:
        story.append(Paragraph(f"Soru: {report.question}", meta_style))
    story.append(Spacer(1, 0.4 * cm))

    # --- Özet ---
    if report.summary:
        story.append(Paragraph("Özet", heading_style))
        story.append(Paragraph(report.summary, body_style))

    # --- Metrikler ---
    if report.metrics:
        story.append(Paragraph("Metrikler", heading_style))
        metric_rows = [["Metrik", "Değer"]]
        metric_rows += [[str(k), str(v)] for k, v in report.metrics.items()]
        story.append(_make_table(metric_rows, font, font_bold, doc.width))

    # --- Aksiyon planı ---
    action_rows = report.action_rows()
    if action_rows:
        story.append(Paragraph("Aksiyon Planı", heading_style))
        items = []
        for row in action_rows:
            prefix = f"<b>[{row['priority']}]</b> " if row["priority"] else ""
            text = f"{prefix}{row['action']}"
            if row["reason"]:
                text += f"<br/><font size=9 color='#666666'>{row['reason']}</font>"
            items.append(ListItem(Paragraph(text, body_style), leftIndent=12))
        story.append(ListFlowable(items, bulletType="bullet", start="•"))

        if report.action_reasoning:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(f"<i>{report.action_reasoning}</i>", meta_style))

    # --- Grafik verisi (tablo olarak) ---
    if report.chart_data:
        story.append(Paragraph("Veri", heading_style))
        df = pd.DataFrame(report.chart_data)
        truncated = len(df) > MAX_PDF_CHART_ROWS
        df = df.head(MAX_PDF_CHART_ROWS).iloc[:, :MAX_PDF_TABLE_COLS]

        table_rows = [[str(c) for c in df.columns]]
        table_rows += [[str(v) for v in row] for row in df.itertuples(index=False)]
        story.append(_make_table(table_rows, font, font_bold, doc.width))

        if truncated:
            story.append(Spacer(1, 0.2 * cm))
            story.append(
                Paragraph(
                    f"Not: İlk {MAX_PDF_CHART_ROWS} satır gösterilmektedir. "
                    "Tam veri için Excel çıktısını kullanın.",
                    meta_style,
                )
            )

    # --- Sorgu (varsa, en sonda; şeffaflık için) ---
    if report.sql_query:
        story.append(Paragraph("Çalıştırılan Sorgu", heading_style))
        story.append(Paragraph(f"<font face='Courier' size=9>{report.sql_query}</font>",
                               body_style))

    doc.build(story)
    return buffer.getvalue()


def _make_table(rows: list[list[str]], font: str, font_bold: str, width: float) -> Table:
    """Başlık satırı vurgulanmış, sayfaya sığan basit bir tablo üretir."""
    col_count = max(len(r) for r in rows)
    table = Table(rows, colWidths=[width / col_count] * col_count, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTNAME", (0, 1), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b0b0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


# ---------------------------------------------------------------------------
# Ortak giriş noktası
# ---------------------------------------------------------------------------
def export_report(payload: dict[str, Any], export_format: str) -> tuple[bytes, str, str]:
    """
    Raporu istenen formata çevirir.

    Returns: (dosya_içeriği, dosya_adı, mime_type)
    Raises: ValueError — desteklenmeyen format.
    """
    report = ReportDocument.from_payload(payload)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    if export_format == "excel":
        return (
            build_excel(report),
            f"rapor_{stamp}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    if export_format == "pdf":
        return build_pdf(report), f"rapor_{stamp}.pdf", "application/pdf"

    raise ValueError(f"Desteklenmeyen format: {export_format}. 'pdf' veya 'excel' olmalı.")


# ---------------------------------------------------------------------------
# Hızlı test — python -m src.services.report_exporter
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    demo_payload = {
        "title": "Haftalık Satış Tahmini",
        "question": "Önümüzdeki hafta satışlar ne olur?",
        "summary": (
            "Önümüzdeki hafta satışlarda %13.51 artış bekleniyor; toplam 13825 "
            "birime ulaşılacağı öngörülüyor. Şu ana kadarki veride eksik ve "
            "aykırı değerler temizlendi."
        ),
        "sql_query": "SELECT ds, amount FROM sales ORDER BY ds;",
        "chart_data": [
            {"ds": "2026-06-11", "yhat": 1850.0},
            {"ds": "2026-06-12", "yhat": 1900.0},
            {"ds": "2026-06-13", "yhat": 1930.0},
        ],
        "action_details": [
            {"action": "Stok seviyelerini gözden geçirin.", "priority": "high",
             "reason": "Beklenen %13.51 artış için ürün bulunurluğu şart."},
            {"action": "Operasyonel kapasiteyi değerlendirin.", "priority": "medium",
             "reason": "Günlük ortalama 1975 birim satış öngörülüyor."},
        ],
        "action_reasoning": "Artış trendi güçlü ve tahmin hata payı düşük (%6.4).",
        "metrics": {"selected_model": "prophet", "mape_percent": 6.4,
                    "change_percent": 13.51, "trend": "artış"},
    }

    out_dir = Path("exports")
    out_dir.mkdir(exist_ok=True)

    for fmt in ("pdf", "excel"):
        content, filename, mime = export_report(demo_payload, fmt)
        path = out_dir / filename
        path.write_bytes(content)
        print(f"{fmt:6} → {path}  ({len(content):,} byte, {mime})")