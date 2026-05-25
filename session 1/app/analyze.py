import csv
import os
from collections import Counter
from logger import get_logger

logger = get_logger(__name__)

_default_data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.environ.get("DATA_DIR", _default_data_dir)
INPUT_FILE = os.path.join(DATA_DIR, "books.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "analyze.csv")


def analyze():
    if not os.path.exists(INPUT_FILE):
        logger.error("books.csv introuvable — analyze() annulée")
        return

    books = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            books.append(row)

    logger.info(f"{len(books)} lignes chargées depuis books.csv")

    prices = []
    for b in books:
        try:
            if b.get("price"):
                prices.append(float(b["price"]))
        except ValueError:
            logger.warning(f"Prix ignoré (valeur invalide) : '{b.get('price')}'")

    ratings = []
    for b in books:
        try:
            if b.get("rating"):
                ratings.append(int(b["rating"]))
        except ValueError:
            logger.warning(f"Note ignorée (valeur invalide) : '{b.get('rating')}'")

    categories = Counter(b["category"] for b in books if b.get("category"))
    scraping_dates = sorted(set(b["scraping_date"] for b in books if b.get("scraping_date")))

    stats = [
        {"métrique": "total_livres", "valeur": len(books)},
        {"métrique": "nb_scrappings", "valeur": len(scraping_dates)},
        {"métrique": "dernier_scrapping", "valeur": scraping_dates[-1] if scraping_dates else ""},
        {"métrique": "prix_moyen", "valeur": round(sum(prices) / len(prices), 2) if prices else 0},
        {"métrique": "prix_min", "valeur": round(min(prices), 2) if prices else 0},
        {"métrique": "prix_max", "valeur": round(max(prices), 2) if prices else 0},
        {"métrique": "note_moyenne", "valeur": round(sum(ratings) / len(ratings), 2) if ratings else 0},
        {"métrique": "nb_categories", "valeur": len(categories)},
    ]

    for note in range(1, 6):
        stats.append({"métrique": f"livres_note_{note}", "valeur": sum(1 for r in ratings if r == note)})

    for cat, count in categories.most_common(10):
        stats.append({"métrique": f"top_cat_{cat}", "valeur": count})

    try:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["métrique", "valeur"])
            writer.writeheader()
            writer.writerows(stats)
        logger.info(f"Analyse exportée dans analyze.csv ({len(stats)} métriques)")
    except IOError as e:
        logger.error(f"Impossible d'écrire analyze.csv : {e}")


if __name__ == "__main__":
    analyze()
