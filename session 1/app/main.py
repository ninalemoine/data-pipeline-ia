import csv
import sys
import os
from datetime import datetime

# Permet d'importer scraper et transform depuis le dossier app/
sys.path.append(os.path.dirname(__file__))

from scraper import get_all_page_links, get_book_links_from, get_book_infos_from
from transform import clean_books
from analyze import analyze

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")


def main():
    # 1. Récupérer les liens de toutes les pages (50 pages au total)
    page_links = get_all_page_links(50)

    # 2. Récupérer les liens de chaque livre
    book_links = []
    for page_link in page_links:
        print(f"Scraping page : {page_link}")
        book_links += get_book_links_from(page_link)

    print(f"\n{len(book_links)} livres trouvés. Récupération des infos...\n")

    # 3. Récupérer les infos de chaque livre
    books = []
    for book_link in book_links:
        print(f"  -> {book_link}")
        infos = get_book_infos_from(book_link)
        books.append(infos)

    # 4. Nettoyer les données
    books = clean_books(books)

    # 5. Ajouter la date du scraping à chaque livre
    scraping_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for book in books:
        book["scraping_date"] = scraping_date

    # 6. Ajouter les données au CSV existant (ou le créer s'il n'existe pas)
    file_exists = os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price", "rating", "category", "scraping_date"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(books)

    print(f"\n{len(books)} livres exportés dans data/books.csv")

    # 7. Mettre à jour l'analyse
    analyze()


if __name__ == "__main__":
    main()
