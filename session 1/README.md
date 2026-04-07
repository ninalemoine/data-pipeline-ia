# Data Pipeline — books.toscrape.com

Pipeline de scraping automatisé de 1000 livres depuis [books.toscrape.com](https://books.toscrape.com), avec nettoyage des données, analyse statistique, et exécution planifiée via Docker + cron.

## Structure du projet

```
session 1/
├── app/
│   ├── main.py        # Orchestration du pipeline
│   ├── scraper.py     # Scraping HTTP (avec retry, timeout, rate limiting)
│   ├── transform.py   # Nettoyage et normalisation des données
│   └── analyze.py     # Calcul des statistiques et export
├── data/
│   ├── books.csv      # Données brutes (cumulées à chaque run)
│   └── analyze.csv    # Métriques calculées (écrasé à chaque run)
├── doc/
│   └── pipeline_schema.pdf
├── Dockerfile
├── docker-compose.yml
├── crontab.sh         # Planification cron (toutes les 30 min)
├── requirements.txt
└── README.md
```

## Données collectées

Pour chaque livre :

| Champ | Description |
|-------|-------------|
| `title` | Titre du livre |
| `price` | Prix en livres sterling (float) |
| `rating` | Note de 1 à 5 (int) |
| `category` | Catégorie du livre |
| `scraping_date` | Horodatage du scraping |

## Lancer avec Docker (recommandé)

```bash
# Build et démarrage en arrière-plan
docker compose up -d --build

# Vérifier que le container tourne
docker ps

# Lancer le pipeline manuellement sans attendre le cron
docker exec python-app python3 /app/main.py

# Consulter les logs du cron
docker exec python-app cat /app/result.output

# Arrêter
docker compose down
```

Le cron exécute `main.py` automatiquement **toutes les 30 minutes**.

## Lancer sans Docker

```bash
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install -r requirements.txt

python app/main.py
```

## Fonctionnement du pipeline

```
get_all_page_links()        → 50 URLs de pages catalogue
      ↓
get_book_links_from()       → ~1000 URLs de livres (avec retry + rate limit)
      ↓
get_book_infos_from()       → titre, prix, note, catégorie par livre
      ↓
clean_books()               → nettoyage prix (£ → float), valeurs manquantes
      ↓
books.csv                   → append (données cumulées entre les runs)
      ↓
analyze()                   → statistiques exportées dans analyze.csv
```

## Robustesse

- **Timeout** : chaque requête HTTP est limitée à 10 secondes
- **Retry** : 3 tentatives automatiques en cas d'échec réseau
- **Rate limiting** : délai de 0.5s entre chaque requête (évite le ban IP)
- **Données corrompues** : les prix et notes invalides sont ignorés avec un warning, le pipeline continue
- **Fichier manquant** : `analyze()` vérifie l'existence de `books.csv` avant de l'ouvrir
- **Dossier data** : créé automatiquement au build Docker (`mkdir -p /app/data`)

## Ouvrir le CSV dans Excel

Excel en locale française utilise le point-virgule comme séparateur. Pour ouvrir correctement le fichier :
- Dans Excel : *Données > À partir d'un fichier texte/CSV*, choisir la **virgule** comme délimiteur
