"""
Rapor endpoint'leri — Swagger/OpenAPI şablonu.

FS Notları:
- Dashboard ana sayfası `/reports` ile geçmiş raporları listeler.
- `/reports/{report_id}` ile detay sayfası açılır.
- Rapor içeriği chat yanıtıyla aynı JSON yapısını kullanır (tutarlı frontend modeli).
"""
from fastapi import APIRouter, HTTPException, status

from src.api.v1.schemas.common import ErrorResponse
from src.api.v1.schemas.reports import ReportListResponse, ReportResponse, ReportSummary

router = APIRouter()


@router.get(
    "",
    response_model=ReportListResponse,
    summary="Rapor listesini getir",
    description=(
        "Kullanıcının daha önce oluşturduğu tüm raporların özet listesini döner. "
        "Dashboard ana sayfasındaki rapor kartları bu endpoint'i kullanır."
    ),
    response_description="Rapor özet kartları listesi.",
    responses={
        500: {"model": ErrorResponse, "description": "Rapor listesi alınamadı"},
    },
)
def list_reports() -> ReportListResponse:
    """Geçmiş raporların özet listesini döner."""
    # TODO(Sprint-3): Veritabanı / depolama entegrasyonu
    return ReportListResponse(
        total=1,
        reports=[
            ReportSummary(
                report_id="rpt_template_001",
                title="Örnek Satış Tahmini",
                created_at="2026-07-04T12:00:00+03:00",
                status="completed",
            )
        ],
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Rapor detayını getir",
    description=(
        "Belirtilen rapor kimliğine ait tam içeriği döner: özet, grafik datası ve aksiyon planı. "
        "Frontend rapor detay sayfası bu endpoint'i kullanır."
    ),
    response_description="Raporun tam içeriği.",
    responses={
        404: {"model": ErrorResponse, "description": "Rapor bulunamadı"},
        500: {"model": ErrorResponse, "description": "Rapor okunamadı"},
    },
)
def get_report(report_id: str) -> ReportResponse:
    """Tek bir raporun detayını döner."""
    if report_id == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapor bulunamadı.",
        )

    # TODO(Sprint-3): report_id ile depodan okuma
    return ReportResponse(
        report_id=report_id,
        status="success",
        summary="Şablon rapor — gerçek veri Sprint 3'te eklenecek.",
        chart_data=[{"date": "2026-07-01", "predicted_sales": 12000}],
        action_plan=["Örnek aksiyon maddesi."],
    )
