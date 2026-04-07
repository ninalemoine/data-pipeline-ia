import csv
import os
from collections import Counter

INPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "analyze.csv")


def analyze():
    if not os.path.exists(INPUT_FILE):
        print("ERROR - books.csv introuvable, analyze() annulée")
        return

    books = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            books.append(row)

    prices = []
    for b in books:
        try:
            if b.get("price"):
                prices.append(float(b["price"]))
        except ValueError:
            print(f"WARN - Prix ignoré (valeur invalide) : '{b.get('price')}'")

    ratings = []
    for b in books:
        try:
            if b.get("rating"):
                ratings.append(int(b["rating"]))
        except ValueError:
            print(f"WARN - Note ignorée (valeur invalide) : '{b.get('rating')}'")

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
        nb = sum(1 for r in ratings if r == note)
        stats.append({"métrique": f"livres_note_{note}", "valeur": nb})

    for cat, count in categories.most_common(10):
        stats.append({"métrique": f"top_cat_{cat}", "valeur": count})

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["métrique", "valeur"])
        writer.writeheader()
        writer.writerows(stats)

    print(f"Analyse exportée dans data/analyze.csv ({len(stats)} métriques)")


if __name__ == "__main__":
    analyze()
