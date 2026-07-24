"""
LangChain LLM kurulumu. Tüm ajanlar modeli bu tek fonksiyondan çağıracak;
böylece model/ayar değişikliği tek yerden yapılır.
"""
import locale
import os
import sys

# Windows'ta httpx ASCII encoding kullanıyor; Python'un varsayılan
# encoding'ini UTF-8'e zorla (httpx import edilmeden önce).
if sys.platform == "win32":
    # Python 3.15+ için önerilen yöntem (PEP 686)
    if not sys.flags.utf8_mode:
        os.environ.setdefault("PYTHONUTF8", "1")
    
    # Locale ayarla
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, "tr_TR.UTF-8")
        except locale.Error:
            pass

# sys.getdefaultencoding() değiştirilemez ama yeni string'ler için varsayılanı belirle
if hasattr(sys, "_enablelegacywindowsfsencoding"):
    # Python 3.6+ Windows için
    sys._enablelegacywindowsfsencoding = lambda: None  # type: ignore

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# httpx'in header encoding'ini UTF-8'e zorla (Windows ASCII sorununu çöz)
try:
    import httpx._models
    original_normalize = httpx._models._normalize_header_value
    
    def _normalize_header_value_utf8(value: str | bytes, encoding: str | None = None) -> bytes:
        """Monkey patch: httpx header encoding'ini UTF-8'e zorla."""
        return original_normalize(value, encoding or "utf-8")
    
    httpx._models._normalize_header_value = _normalize_header_value_utf8
except (ImportError, AttributeError):
    pass  # httpx yoksa veya API değişmişse sessizce atla

load_dotenv()  # .env dosyasındaki anahtarları okur


def get_llm():
    """
    Yapılandırılmış Gemini modelini döndürür.
    temperature=0 -> tutarlı, tekrarlanabilir cevaplar (SQL üretimi için ideal).


    """
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0,
    )


# Hızlı test:  python -m src.agents.llm
if __name__ == "__main__":
    llm = get_llm()
    cevap = llm.invoke("Tek cümleyle kendini tanıt.")
    print(cevap.content)