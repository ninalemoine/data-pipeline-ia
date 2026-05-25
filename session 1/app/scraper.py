import os
import time
import requests
from bs4 import BeautifulSoup
from logger import get_logger
from chaos import maybe_raise_network_error, maybe_drop_field, maybe_raise_http_429

logger = get_logger(__name__)

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
REQUEST_TIMEOUT = 10
RETRY_COUNT = 3
RATE_LIMIT_DELAY = 0.2
HTTP_429_BACKOFF = int(os.environ.get("HTTP_429_BACKOFF", "60"))  # configurable pour les tests


def _get(url: str) -> requests.Response:
    """Requête HTTP avec timeout, retry automatique et gestion HTTP 429."""
    for attempt in range(RETRY_COUNT):
        try:
            maybe_raise_network_error(url)
            response = requests.get(url, timeout=REQUEST_TIMEOUT)

            # Rate limit : on attend avant de réessayer
            if response.status_code == 429 or maybe_raise_http_429():
                logger.warning(f"HTTP 429 reçu — pause de {HTTP_429_BACKOFF}s avant retry")
                time.sleep(HTTP_429_BACKOFF)
                continue

            return response

        except requests.RequestException as e:
            logger.warning(f"Tentative {attempt + 1}/{RETRY_COUNT} échouée pour {url} : {e}")
            time.sleep(1)

    logger.error(f"Abandon après {RETRY_COUNT} tentatives : {url}")
    return None


def get_all_page_links(total_pages: int) -> list:
    urls = [f"https://books.toscrape.com/catalogue/page-{page}.html"
            for page in range(1, total_pages + 1)]
    logger.info(f"{total_pages} pages à scraper générées")
    return urls


def get_book_links_from(page_link: str) -> list:
    domain = "https://books.toscrape.com/catalogue/"
    response = _get(page_link)
    if response is None:
        return []

    links = []
    if response.status_code != 200:
        logger.error(f"Status code {response.status_code} pour {page_link}")
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        all_tag_div = soup.find_all("div", class_="image_container")
        for tag_div in all_tag_div:
            a_tag = tag_div.find("a")
            if a_tag and a_tag.get("href"):
                links.append(domain + a_tag["href"])

    time.sleep(RATE_LIMIT_DELAY)
    return links


def get_book_infos_from(book_link: str) -> dict:
    response = _get(book_link)
    if response is None:
        return {}

    if response.status_code != 200:
        logger.error(f"Status code {response.status_code} pour {book_link}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    try:
        # maybe_drop_field() simule un élément HTML manquant
        h1 = None if maybe_drop_field() else soup.find("h1")
        title = h1.text if h1 else None

        price_tag = soup.find("p", class_="price_color")
        price = price_tag.text.strip() if price_tag else None

        rating_tag = soup.find("p", class_="star-rating")
        rating_word = rating_tag["class"][1] if rating_tag else None
        rating = RATINGS.get(rating_word, 0) if rating_word else 0

        breadcrumb = soup.find("ul", class_="breadcrumb")
        items = breadcrumb.find_all("li") if breadcrumb else []
        category = items[2].text.strip() if len(items) > 2 else None

        if not all([title, price, category]):
            logger.warning(f"Données incomplètes sur {book_link} — livre ignoré")
            return {}

    except (AttributeError, IndexError, TypeError, KeyError) as e:
        logger.error(f"Erreur de parsing sur {book_link} : {e}")
        return {}

    time.sleep(RATE_LIMIT_DELAY)
    return {"title": title, "price": price, "rating": rating, "category": category}
