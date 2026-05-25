"""
Tests de robustesse du pipeline.
Chaque test simule une erreur réelle qui pourrait arriver en production.

Lancer les tests :
  cd "session 1"
  python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import unittest
from bs4 import BeautifulSoup
from transform import clean_price, clean_books


# ─────────────────────────────────────────────
# TESTS : clean_price()
# ─────────────────────────────────────────────

class TestCleanPrice(unittest.TestCase):

    def test_prix_normal(self):
        """Cas nominal : prix bien formé."""
        self.assertEqual(clean_price("£12.99"), 12.99)

    def test_prix_sans_symbole(self):
        """Le site oublie le symbole £."""
        self.assertEqual(clean_price("12.99"), 12.99)

    def test_prix_encodage_corrompu(self):
        """Encodage UTF-8 cassé : Â devant le £."""
        self.assertEqual(clean_price("Â£12.99"), 12.99)

    def test_prix_chaine_vide(self):
        """Balise présente mais vide."""
        self.assertEqual(clean_price(""), 0.0)

    def test_prix_none(self):
        """Balise absente → None passé à clean_price."""
        self.assertEqual(clean_price(None), 0.0)

    def test_prix_texte_invalide(self):
        """Valeur impossible : le site a changé de format."""
        self.assertEqual(clean_price("N/A"), 0.0)

    def test_prix_avec_espaces(self):
        """Espaces parasites autour de la valeur."""
        self.assertEqual(clean_price("  £ 12.99  "), 12.99)

    def test_prix_virgule_au_lieu_de_point(self):
        """Format européen avec virgule décimale."""
        # Retourne 0.0 car "12,99" n'est pas castable en float
        self.assertEqual(clean_price("£12,99"), 0.0)


# ─────────────────────────────────────────────
# TESTS : clean_books()
# ─────────────────────────────────────────────

class TestCleanBooks(unittest.TestCase):

    def test_livre_complet(self):
        """Cas nominal : toutes les clés présentes."""
        books = [{"title": "Dune", "price": "£9.99", "rating": 5, "category": "Sci-Fi"}]
        result = clean_books(books)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], 9.99)

    def test_liste_vide(self):
        """Aucun livre scrappé."""
        self.assertEqual(clean_books([]), [])

    def test_livre_vide(self):
        """Scraper a retourné {} pour un livre."""
        result = clean_books([{}])
        self.assertEqual(result, [])

    def test_livre_sans_prix(self):
        """Clé price absente du dict."""
        books = [{"title": "Dune", "rating": 5, "category": "Sci-Fi"}]
        result = clean_books(books)
        self.assertEqual(result[0]["price"], 0.0)

    def test_livre_sans_categorie(self):
        """Clé category absente."""
        books = [{"title": "Dune", "price": "£9.99", "rating": 5}]
        result = clean_books(books)
        self.assertEqual(result[0]["category"], "Unknown")

    def test_melange_livres_valides_et_invalides(self):
        """Mix de livres OK et vides — seuls les valides passent."""
        books = [
            {"title": "Dune", "price": "£9.99", "rating": 5, "category": "Sci-Fi"},
            {},
            {"title": "1984", "price": "£7.50", "rating": 4, "category": "Fiction"},
        ]
        result = clean_books(books)
        self.assertEqual(len(result), 2)


# ─────────────────────────────────────────────
# TESTS : parsing HTML
# ─────────────────────────────────────────────

class TestParsingHTML(unittest.TestCase):

    def _parse(self, html: str) -> dict:
        """Helper : simule ce que fait get_book_infos_from() sur un HTML donné."""
        from scraper import RATINGS
        soup = BeautifulSoup(html, "html.parser")
        try:
            title = soup.find("h1").text if soup.find("h1") else None
            price_tag = soup.find("p", class_="price_color")
            price = price_tag.text.strip() if price_tag else None
            rating_tag = soup.find("p", class_="star-rating")
            rating_word = rating_tag["class"][1] if rating_tag else None
            rating = RATINGS.get(rating_word, 0) if rating_word else 0
            breadcrumb = soup.find("ul", class_="breadcrumb")
            items = breadcrumb.find_all("li") if breadcrumb else []
            category = items[2].text.strip() if len(items) > 2 else None
            if not all([title, price, category]):
                return {}
        except (AttributeError, IndexError, TypeError, KeyError):
            return {}
        return {"title": title, "price": price, "rating": rating, "category": category}

    def test_html_complet(self):
        """HTML bien formé → livre complet."""
        html = """
        <h1>Dune</h1>
        <p class="price_color">£9.99</p>
        <p class="star-rating Five"></p>
        <ul class="breadcrumb">
            <li>Home</li><li>Books</li><li>Sci-Fi</li>
        </ul>
        """
        result = self._parse(html)
        self.assertEqual(result["title"], "Dune")
        self.assertEqual(result["price"], "£9.99")
        self.assertEqual(result["category"], "Sci-Fi")

    def test_h1_manquant(self):
        """Le site change de structure : plus de balise h1."""
        html = """
        <p class="price_color">£9.99</p>
        <p class="star-rating Five"></p>
        <ul class="breadcrumb"><li>Home</li><li>Books</li><li>Sci-Fi</li></ul>
        """
        self.assertEqual(self._parse(html), {})

    def test_prix_manquant(self):
        """Balise price_color absente."""
        html = """
        <h1>Dune</h1>
        <p class="star-rating Five"></p>
        <ul class="breadcrumb"><li>Home</li><li>Books</li><li>Sci-Fi</li></ul>
        """
        self.assertEqual(self._parse(html), {})

    def test_breadcrumb_trop_court(self):
        """Breadcrumb présent mais pas assez de niveaux → catégorie absente."""
        html = """
        <h1>Dune</h1>
        <p class="price_color">£9.99</p>
        <p class="star-rating Five"></p>
        <ul class="breadcrumb"><li>Home</li></ul>
        """
        self.assertEqual(self._parse(html), {})

    def test_classe_css_renommee(self):
        """Le dev du site renomme 'price_color' en 'price' → balise introuvable."""
        html = """
        <h1>Dune</h1>
        <p class="price">£9.99</p>
        <p class="star-rating Five"></p>
        <ul class="breadcrumb"><li>Home</li><li>Books</li><li>Sci-Fi</li></ul>
        """
        self.assertEqual(self._parse(html), {})

    def test_html_vide(self):
        """Réponse HTTP vide."""
        self.assertEqual(self._parse(""), {})

    def test_html_completement_different(self):
        """Le site a fait une refonte totale."""
        html = "<div class='product'><span>Dune</span></div>"
        self.assertEqual(self._parse(html), {})


if __name__ == "__main__":
    unittest.main()
