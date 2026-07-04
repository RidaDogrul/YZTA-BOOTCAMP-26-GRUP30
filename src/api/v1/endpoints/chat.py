"""
Chat endpoint'leri — Swagger/OpenAPI şablonu.

FS Notları:
- Kullanıcı chat arayüzünden doğal dil sorusu gönderir.
- Backend Orchestrator → SQL Executor → Data Scientist → Insight Generator akışını tetikler.
- Yanıt; özet metin, grafik datası ve aksiyon planını tek JSON içinde döner.
"""
from fastapi import APIRouter, HTTPException, status

from src.api.v1.schemas.chat import ChatRequest, ChatResponse
from src.api.v1.schemas.common import ErrorResponse

router = APIRouter()


@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Doğal dilde soru sor",
    description=(
        "Kullanıcının analiz/tahmin sorusunu alır, arka planda ajan pipeline'ını çalıştırır "
        "ve yapılandırılmış sonuç döner. Frontend chat balonları bu yanıtı render eder."
    ),
    response_description="Özet, SQL, grafik verisi ve aksiyon planı.",
    responses={
        400: {"model": ErrorResponse, "description": "Eksik session_id veya geçersiz soru"},
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
        500: {"model": ErrorResponse, "description": "Ajan pipeline hatası"},
    },
)
def ask_question(payload: ChatRequest) -> ChatResponse:
    """
    Örnek request:
    ```json
    {
      "session_id": "sess_abc123",
      "question": "Önümüzdeki ay en çok satış yapılacak kategori hangisi?"
    }
    ```
    """
    if not payload.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id boş olamaz.",
        )

    # TODO(Sprint-2): Orchestrator entegrasyonu
    return ChatResponse(
        status="success",
        summary="Şablon yanıt — gerçek ajan cevabı Sprint 2'de eklenecek.",
        sql_query="SELECT category, SUM(revenue) FROM sales GROUP BY category",
        chart_data=[{"date": "2026-07-01", "predicted_sales": 12000}],
        action_plan=["Örnek aksiyon maddesi."],
    )
