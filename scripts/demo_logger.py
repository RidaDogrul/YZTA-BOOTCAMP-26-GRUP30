from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.utils.logger import clear_request_id, get_logger, set_request_id


def main():
    """
    Logger kullanımını gösteren basit demo.

    Bu demo:
    - request_id takibini gösterir.
    - JSON formatlı log çıktısı üretir.
    - Log içindeki hassas verilerin maskelendiğini gösterir.
    """

    set_request_id("req-demo-logger-001")
    logger = get_logger("demo.logger")

    logger.info(
        "Kullanıcı sisteme giriş yaptı. Email: test@example.com Telefon: 05551234567"
    )

    logger.info(
        "Sipariş kaydı işlendi.",
        extra={
            "customer_name": "John Smith",
            "email": "john@example.com",
            "phone": "05551234567",
            "tckn": "10000000146",
            "order_id": "ORD-1001",
            "total_amount": 2450.75,
            "category": "electronics",
        },
    )

    logger.warning(
        "API isteğinde hassas anahtar bilgisi yakalandı.",
        extra={
            "api_key": "real-api-key-should-not-be-visible",
            "token": "real-token-should-not-be-visible",
            "safe_field": "Bu alan hassas değil.",
        },
    )

    clear_request_id()


if __name__ == "__main__":
    main()