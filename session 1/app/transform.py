from logger import get_logger
from chaos import maybe_corrupt_price

logger = get_logger(__name__)


def clean_price(price: str) -> float:
    # "or" protège contre None et chaîne vide
    raw = maybe_corrupt_price(price or "0")
    try:
        return float(raw.replace("£", "").replace("Â", "").strip())
    except (ValueError, AttributeError) as e:
        logger.warning(f"Prix mal formé '{raw}' : {e}")
        return 0.0


def clean_books(books: list) -> list:
    cleaned = []
    for book in books:
        if not book:
            continue
        cleaned.append({
            "title": book.get("title") or "",
            "price": clean_price(book.get("price") or "0"),
            "rating": book.get("rating") or 0,
            "category": book.get("category") or "Unknown",
        })
    logger.info(f"{len(cleaned)} livres nettoyés sur {len(books)} reçus")
    return cleaned
