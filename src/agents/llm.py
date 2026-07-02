"""
LangChain LLM kurulumu. Tüm ajanlar modeli bu tek fonksiyondan çağıracak;
böylece model/ayar değişikliği tek yerden yapılır.
"""
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()  # .env dosyasındaki anahtarları okur


def get_llm():
    """
    Yapılandırılmış Gemini modelini döndürür.
    temperature=0 -> tutarlı, tekrarlanabilir cevaplar (SQL üretimi için ideal).
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0,
    )


# Hızlı test:  python -m src.agents.llm
if __name__ == "__main__":
    llm = get_llm()
    cevap = llm.invoke("Tek cümleyle kendini tanıt.")
    print(cevap.content)