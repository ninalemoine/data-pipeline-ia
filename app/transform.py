def clean_price(price: str) -> float:
    # Supprime le symbole £ et convertit en nombre décimal
    try:
        return float(price.replace("£", "").replace("Â", "").strip())
    except ValueError as e:
        print(f"ERROR - Prix mal formé '{price}' : {e}")
        return 0.0


def clean_books(books: list) -> list:
    cleaned = []
    for book in books:
        if not book:
            continue
        cleaned.append({
            "title": book["title"],
            "price": clean_price(book["price"]),
            "rating": book["rating"],
            "category": book["category"],
        })
    return cleaned
