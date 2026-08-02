"""
LangChain LLM kurulumu. Tüm ajanlar modeli bu tek fonksiyondan çağıracak;
böylece model/ayar değişikliği tek yerden yapılır.
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm():
    """
    Yapılandırılmış OpenAI modelini döndürür.
    temperature=0 -> tutarlı, tekrarlanabilir cevaplar (SQL üretimi için ideal).
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,
    )


# Hızlı test:  python -m src.agents.llm
if __name__ == "__main__":
    llm = get_llm()
    cevap = llm.invoke("Tek cümleyle kendini tanıt.")
    print(cevap.content)
