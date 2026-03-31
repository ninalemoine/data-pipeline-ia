import requests
from bs4 import BeautifulSoup

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def get_all_page_links(total_pages: int) -> list:
    urls = []
    for page in range(1, total_pages + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        urls.append(url)
    return urls


def get_book_links_from(page_link: str) -> list:
    domain = "https://books.toscrape.com/catalogue/"
    try:
        response = requests.get(page_link)
    except Exception as e:
        print(f"ERROR - Impossible de contacter la page : {e}")
        return []

    links = []
    if response.status_code != 200:
        print(f"ERROR - Status code: {response.status_code}")
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        all_tag_div = soup.find_all("div", class_="image_container")
        for tag_div in all_tag_div:
            link = domain + tag_div.find("a").get("href")
            links.append(link)
    return links


def get_book_infos_from(book_link: str) -> dict:
    try:
        response = requests.get(book_link)
    except Exception as e:
        print(f"ERROR - Impossible de contacter le livre : {e}")
        return {}

    if response.status_code != 200:
        print(f"ERROR - Status code: {response.status_code}")
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

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "category": category,
    }
