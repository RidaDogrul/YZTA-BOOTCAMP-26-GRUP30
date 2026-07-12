"""
Chat endpoints for natural language data questions.

Sprint 2 scope:
- Accept a user question from the chat interface.
- Validate the active data source session id.
- Return a structured response for the frontend.
- Integrate with the real orchestrator when it becomes available.
"""

from fastapi import APIRouter, HTTPException, status
from src.utils.cache import make_cache_key, query_cache
from src.api.v1.schemas.chat import ChatRequest, ChatResponse
from src.api.v1.schemas.common import ErrorResponse

router = APIRouter()
CHAT_CACHE_TTL_SECONDS = 300.0
def _build_chat_cache_key(payload: ChatRequest) -> str:
    """Build a deterministic cache key for chat requests."""
    return make_cache_key(
        "chat",
        payload.session_id.strip(),
        payload.question.strip(),
    )

def _mock_orchestrator_response(payload: ChatRequest) -> ChatResponse:
    """
    Temporary mock response for Sprint 2.

    This keeps the Chat API usable while the real orchestrator,
    SQL executor and insight generator are still being integrated.
    """
    return ChatResponse(
        status="success",
        summary=(
            "Bu cevap geçici mock orchestrator çıktısıdır. "
            "Gerçek ajan entegrasyonu Sprint 2 içinde eklenecektir."
        ),
        sql_query="SELECT category, SUM(revenue) AS total_revenue FROM sales GROUP BY category",
        chart_data=[
            {"category": "Tekstil", "total_revenue": 12000},
            {"category": "Elektronik", "total_revenue": 9500},
            {"category": "Gıda", "total_revenue": 7800},
        ],
        action_plan=[
            "En yüksek ciro üreten kategoriler için stok seviyelerini kontrol edin.",
            "Düşük performanslı kategoriler için kampanya planı oluşturun.",
        ],
    )


@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Doğal dilde veri analizi sorusu sor",
    description=(
        "Kullanıcının doğal dilde sorduğu analiz veya tahmin sorusunu alır. "
        "Sprint 2 MVP kapsamında şimdilik mock orchestrator response döner. "
        "Gerçek orchestrator entegrasyonu hazır olduğunda bu endpoint aynı response şemasıyla "
        "gerçek ajan akışına bağlanacaktır."
    ),
    response_description="Özet cevap, SQL sorgusu, grafik verisi ve aksiyon planı.",
    responses={
        400: {"model": ErrorResponse, "description": "Eksik session_id veya geçersiz soru"},
        404: {"model": ErrorResponse, "description": "Oturum bulunamadı"},
        500: {"model": ErrorResponse, "description": "Ajan pipeline hatası"},
    },
)
def ask_question(payload: ChatRequest) -> ChatResponse:
    """
    Ask a natural language question about the connected data source.
    """
    if not payload.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id boş olamaz.",
        )

    if not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question boş olamaz.",
        )

    # TODO(Sprint-2): Replace mock response with real orchestrator call.

    cache_key = _build_chat_cache_key(payload)
    cached_response = query_cache.get(cache_key)

    if isinstance(cached_response, ChatResponse):
        return cached_response

    response = _mock_orchestrator_response(payload)
    query_cache.set(
        cache_key,
        response,
        ttl_seconds=CHAT_CACHE_TTL_SECONDS,
    )

    return response