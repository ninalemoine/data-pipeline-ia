import time
import requests
from bs4 import BeautifulSoup

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
REQUEST_TIMEOUT = 10
RETRY_COUNT = 3
RATE_LIMIT_DELAY = 0.5  # secondes entre chaque requête


def _get(url: str) -> requests.Response | None:
    """Requête HTTP avec timeout et retry automatique."""
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            return response
        except requests.RequestException as e:
            print(f"WARN - Tentative {attempt + 1}/{RETRY_COUNT} échouée pour {url} : {e}")
            time.sleep(1)
    print(f"ERROR - Impossible de contacter {url} après {RETRY_COUNT} tentatives")
    return None


def get_all_page_links(total_pages: int) -> list:
    urls = []
    for page in range(1, total_pages + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        urls.append(url)
    return urls


def get_book_links_from(page_link: str) -> list:
    domain = "https://books.toscrape.com/catalogue/"
    response = _get(page_link)
    if response is None:
        return []

    links = []
    if response.status_code != 200:
        print(f"ERROR - Status code {response.status_code} pour {page_link}")
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
        print(f"ERROR - Status code {response.status_code} pour {book_link}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    try:
        title = soup.find("h1").text
        price = soup.find("p", class_="price_color").text.strip()
        rating_word = soup.find("p", class_="star-rating")["class"][1]
        rating = RATINGS.get(rating_word, 0)
        category = soup.find("ul", class_="breadcrumb").find_all("li")[2].text.strip()
    except (AttributeError, IndexError, TypeError) as e:
        print(f"ERROR - Donnée mal formée sur {book_link} : {e}")
        return {}

    time.sleep(RATE_LIMIT_DELAY)
    return {
        "title": title,
        "price": price,
        "rating": rating,
        "category": category,
    }
