import csv
import os
import sys
import time
from datetime import datetime
from logger import get_logger

sys.path.append(os.path.dirname(__file__))

from scraper import get_all_page_links, get_book_links_from, get_book_infos_from
from transform import clean_books
from analyze import analyze

logger = get_logger(__name__)

_default_data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.environ.get("DATA_DIR", _default_data_dir)
OUTPUT_FILE = os.path.join(DATA_DIR, "books.csv")


def _format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m{secs:02d}s" if minutes > 0 else f"{secs}s"


def main():
    start_time = time.time()
    logger.info("=== Démarrage du pipeline ===")

    try:
        # 1. Génération des URLs de pages
        page_links = get_all_page_links(50)

        # 2. Collecte des liens de livres
        book_links = []
        for i, page_link in enumerate(page_links, 1):
            logger.info(f"Scraping page {i}/{len(page_links)}")
            book_links += get_book_links_from(page_link)

        if not book_links:
            logger.error("Aucun lien de livre récupéré — site inaccessible ou structure HTML modifiée. Pipeline arrêté.")
            return

        logger.info(f"{len(book_links)} livres trouvés — récupération des infos...")

        # 3. Scraping de chaque livre
        books_raw = []
        failed = 0
        for book_link in book_links:
            infos = get_book_infos_from(book_link)
            if infos:
                books_raw.append(infos)
            else:
                failed += 1

        scraping_duration = time.time() - start_time
        logger.info(f"Scraping terminé en {_format_duration(scraping_duration)} — {len(books_raw)} OK / {failed} échoués")

        if not books_raw:
            logger.error("Aucun livre scrappé avec succès — export annulé.")
            return

        # 4. Nettoyage des données
        books = clean_books(books_raw)

        # 5. Ajout de l'horodatage
        scraping_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for book in books:
            book["scraping_date"] = scraping_date

        # 6. Export CSV
        try:
            file_exists = os.path.exists(OUTPUT_FILE)
            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["title", "price", "rating", "category", "scraping_date"])
                if not file_exists:
                    writer.writeheader()
                writer.writerows(books)
            logger.info(f"{len(books)} livres exportés dans books.csv")
        except IOError as e:
            logger.error(f"Impossible d'écrire books.csv : {e} — les données de ce run sont perdues")
            return

        # 7. Mise à jour de l'analyse statistique
        analyze()

    except Exception as e:
        logger.error(f"Erreur inattendue — pipeline interrompu : {e}", exc_info=True)
        return

    # 8. Résumé final
    total_duration = time.time() - start_time
    success_rate = round(len(books_raw) / len(book_links) * 100, 1) if book_links else 0
    logger.info(
        f"=== Pipeline terminé en {_format_duration(total_duration)} | "
        f"{len(books_raw)} OK / {failed} échoués ({success_rate}% succès) | "
        f"{len(books)} lignes exportées ==="
    )


if __name__ == "__main__":
    main()
