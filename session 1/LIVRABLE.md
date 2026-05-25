# Data Pipeline for AI — Livrable Final

**Groupe :** Nina LEMOINE · Yoann PAUBERT · Ronny DOUGLAS
**Formation :** MSc Business Analytics — Eugenia School
**Module :** Data Pipelines for AI (3 sessions)
**Date :** Mai 2026
**GitHub :** https://github.com/ninalemoine/data-pipeline-ia

---

## 1. Objectif du projet

Ce projet implémente un pipeline de données automatisé qui collecte, nettoie et analyse les données de 1 000 livres depuis le site [books.toscrape.com](https://books.toscrape.com).

Le pipeline tourne dans un container Docker et s'exécute automatiquement toutes les 30 minutes via une tâche cron. Chaque exécution cumule les données dans un fichier CSV horodaté, permettant de suivre l'évolution des prix et des notes dans le temps.

**Données collectées par livre :**

| Champ | Type | Description |
|-------|------|-------------|
| `title` | string | Titre du livre |
| `price` | float | Prix en livres sterling |
| `rating` | int | Note de 1 à 5 |
| `category` | string | Catégorie du livre |
| `scraping_date` | datetime | Horodatage du run |

---

## 2. Architecture du pipeline

### Schéma du flux de données

```
┌─────────────────────────────────────────────────────┐
│                  Docker Container                    │
│                                                     │
│   CRON (toutes les 30 min)                          │
│        │                                            │
│        ▼                                            │
│   ┌─────────┐    50 pages     ┌──────────────────┐  │
│   │ scraper │ ──────────────► │ 50 URLs catalogue │  │
│   │  .py    │                 └──────────┬───────┘  │
│   │         │ ◄───────────────────────── │          │
│   │         │   1 000 URLs livres        │          │
│   │         │                            ▼          │
│   │         │ ──── 1 requête / livre ──► Site web   │
│   └────┬────┘     (timeout 10s,                     │
│        │           retry 3x,                        │
│        │           rate limit 0.2s)                 │
│        │ 1 000 dicts bruts                          │
│        ▼                                            │
│   ┌─────────┐                                       │
│   │transform│  nettoyage prix, valeurs manquantes   │
│   │  .py    │                                       │
│   └────┬────┘                                       │
│        │ 1 000 dicts propres                        │
│        ▼                                            │
│   ┌─────────┐    append     ┌──────────┐            │
│   │  main   │ ────────────► │books.csv │ (volume)   │
│   │  .py    │               └──────────┘            │
│   │         │               ┌──────────┐            │
│   │         │ ────────────► │analyze   │            │
│   └─────────┘   overwrite   │  .csv    │ (volume)   │
│                             └──────────┘            │
│   ┌─────────┐                                       │
│   │ logger  │ ──► stdout → docker logs              │
│   │  .py    │ ──► logs/pipeline.log (volume)        │
│   └─────────┘                                       │
└─────────────────────────────────────────────────────┘
```

### Structure du projet

```
session 1/
├── app/
│   ├── main.py        # Orchestration du pipeline
│   ├── scraper.py     # Scraping HTTP (retry, timeout, rate limiting)
│   ├── transform.py   # Nettoyage et normalisation
│   ├── analyze.py     # Calcul des statistiques
│   ├── logger.py      # Configuration centralisée des logs
│   └── chaos.py       # Simulation d'erreurs pour les tests
├── data/
│   ├── books.csv      # Données cumulées (append à chaque run)
│   └── analyze.csv    # Statistiques recalculées (overwrite)
├── logs/
│   └── pipeline.log   # Logs persistants sur le volume Docker
├── tests/
│   └── test_pipeline.py  # 21 tests unitaires
├── Dockerfile
├── docker-compose.yml
├── crontab.sh
└── requirements.txt
```

---

## 3. Extraits commentés du code

### 3.1 Scraper — robustesse réseau (`scraper.py`)

```python
def _get(url: str) -> requests.Response:
    """
    Requête HTTP avec trois niveaux de protection :
    - timeout : évite qu'une requête bloque le pipeline indéfiniment
    - retry   : réessaie jusqu'à 3 fois en cas d'erreur réseau
    - HTTP 429: attend avant de réessayer si le serveur rate-limite
    """
    for attempt in range(RETRY_COUNT):          # RETRY_COUNT = 3
        try:
            maybe_raise_network_error(url)      # injecte une erreur si CHAOS_MODE=1
            response = requests.get(url, timeout=REQUEST_TIMEOUT)  # timeout = 10s

            if response.status_code == 429 or maybe_raise_http_429():
                # Le serveur nous dit "trop de requêtes" — on attend avant de continuer
                logger.warning(f"HTTP 429 — pause de {HTTP_429_BACKOFF}s avant retry")
                time.sleep(HTTP_429_BACKOFF)
                continue

            return response

        except requests.RequestException as e:
            logger.warning(f"Tentative {attempt + 1}/{RETRY_COUNT} échouée : {e}")
            time.sleep(1)

    logger.error(f"Abandon après {RETRY_COUNT} tentatives : {url}")
    return None  # la fonction appelante vérifie None et skip le livre
```

**Choix justifiés :**
- `timeout=10` : sans timeout, une requête peut bloquer le cron indéfiniment
- 3 tentatives : équilibre entre résilience et temps d'exécution
- Retour `None` plutôt qu'exception : permet au pipeline de continuer sur les livres suivants

---

### 3.2 Transform — protection contre les valeurs corrompues (`transform.py`)

```python
def clean_price(price: str) -> float:
    # "or" protège contre None ET chaîne vide en une seule ligne
    raw = maybe_corrupt_price(price or "0")
    try:
        # Double remplacement : encodage UTF-8 normal (£) et cassé (Â£)
        return float(raw.replace("£", "").replace("Â", "").strip())
    except (ValueError, AttributeError) as e:
        # Si la valeur est "N/A", "abc", None → on retourne 0.0 sans crasher
        logger.warning(f"Prix mal formé '{raw}' : {e}")
        return 0.0

def clean_books(books: list) -> list:
    cleaned = []
    for book in books:
        if not book:          # filtre les dicts vides retournés par le scraper
            continue
        cleaned.append({
            "title":    book.get("title")    or "",
            "price":    clean_price(book.get("price") or "0"),
            "rating":   book.get("rating")   or 0,
            "category": book.get("category") or "Unknown",
        })
    return cleaned
```

**Choix justifiés :**
- `.get()` au lieu de `[]` : un livre avec une clé manquante ne crash pas le pipeline
- `or "0"` : protège contre `None` retourné par `.get()` si la clé vaut `None`
- Valeur par défaut `"Unknown"` : les données restent exploitables même incomplètes

---

### 3.3 Main — exception globale et monitoring (`main.py`)

```python
def main():
    start_time = time.time()
    logger.info("=== Démarrage du pipeline ===")

    try:
        # ...pipeline...

        if not book_links:
            # Vérification critique : si le site est down, book_links sera vide
            logger.error("Aucun lien récupéré — site inaccessible ou HTML modifié")
            return

        try:
            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
                writer.writerows(books)
        except IOError as e:
            # Protège contre disque plein ou permissions insuffisantes
            logger.error(f"Impossible d'écrire books.csv : {e}")
            return

    except Exception as e:
        # Filet de sécurité global : toute erreur inattendue est loggée
        logger.error(f"Erreur inattendue : {e}", exc_info=True)
        return

    # Résumé final sur une seule ligne
    total_duration = time.time() - start_time
    logger.info(
        f"=== Pipeline terminé en {_format_duration(total_duration)} | "
        f"{len(books_raw)} OK / {failed} échoués ({success_rate}% succès) | "
        f"{len(books)} lignes exportées ==="
    )
```

---

### 3.4 Chaos Mode — simulation d'erreurs (`chaos.py`)

```python
CHAOS_MODE = os.environ.get("CHAOS_MODE", "0") == "1"
CHAOS_RATE = float(os.environ.get("CHAOS_RATE", "0.2"))

def maybe_raise_network_error(url: str) -> None:
    """Simule timeout, connexion refusée ou erreur SSL de façon aléatoire."""
    if CHAOS_MODE and random.random() < CHAOS_RATE:
        raise random.choice([
            requests.exceptions.Timeout("CHAOS: timeout simulé"),
            requests.exceptions.ConnectionError("CHAOS: connexion refusée"),
            requests.exceptions.SSLError("CHAOS: erreur SSL"),
        ])

def maybe_corrupt_price(price: str) -> str:
    """Simule un prix corrompu pour tester clean_price()."""
    if CHAOS_MODE and random.random() < CHAOS_RATE:
        return random.choice(["N/A", "", "??£", "None", "abc"])
    return price
```

**Activation :**
```bash
docker exec -e CHAOS_MODE=1 -e CHAOS_RATE=0.3 -e HTTP_429_BACKOFF=5 \
    python-app python3 /app/main.py
```

---

## 4. Captures d'exécution

### 4.1 Docker Compose — démarrage du container

```
[+] Building 15.2s (16/16) FINISHED
 ✔ Image session1-python-app Built
 ✔ Network session1_default  Created
 ✔ Container python-app      Started
```

### 4.2 Exécution normale — logs complets (run du 2026-05-25)

```
2026-05-25 12:44:28 | INFO     | === Démarrage du pipeline ===
2026-05-25 12:44:28 | INFO     | 50 pages à scraper générées
2026-05-25 12:44:28 | INFO     | Scraping page 1/50
2026-05-25 12:44:29 | INFO     | Scraping page 2/50
...
2026-05-25 12:45:08 | INFO     | Scraping page 50/50
2026-05-25 12:45:09 | INFO     | 1000 livres trouvés — récupération des infos...
2026-05-25 12:57:05 | INFO     | Scraping terminé en 12m37s — 1000 OK / 0 échoués
2026-05-25 12:57:05 | INFO     | 1000 livres nettoyés sur 1000 reçus
2026-05-25 12:57:05 | INFO     | 1000 livres exportés dans books.csv
2026-05-25 12:57:05 | INFO     | 6999 lignes chargées depuis books.csv
2026-05-25 12:57:05 | INFO     | Analyse exportée dans analyze.csv (23 métriques)
2026-05-25 12:57:05 | INFO     | === Pipeline terminé en 12m37s | 1000 OK / 0 échoués (100.0% succès) | 1000 lignes exportées ===
```

### 4.3 Chaos Mode — gestion des erreurs (CHAOS_RATE=0.3)

```
2026-05-25 12:57:15 | WARNING  | ⚠ CHAOS MODE ACTIVÉ — taux d'erreur simulé : 30%
2026-05-25 12:57:15 | INFO     | === Démarrage du pipeline ===
2026-05-25 12:57:15 | WARNING  | CHAOS: erreur réseau injectée sur ...page-1.html
2026-05-25 12:57:15 | WARNING  | Tentative 1/3 échouée : CHAOS: connexion refusée simulée
2026-05-25 12:57:16 | WARNING  | Tentative 2/3 échouée : CHAOS: erreur SSL simulée
2026-05-25 12:57:17 | WARNING  | HTTP 429 reçu — pause de 5s avant retry
2026-05-25 12:57:22 | ERROR    | Abandon après 3 tentatives : ...page-1.html
2026-05-25 12:57:22 | INFO     | Scraping page 2/50
... (le pipeline continue malgré les erreurs)
```

### 4.4 Résultats — books.csv (extrait)

```
title,price,rating,category,scraping_date
A Light in the Attic,51.77,3,Poetry,2026-03-31 11:51:28
Tipping the Velvet,53.74,1,Historical Fiction,2026-03-31 11:51:28
Soumission,50.1,1,Fiction,2026-03-31 11:51:28
```

**Total cumulé après 7 runs : 6 999 lignes**

### 4.5 Résultats — analyze.csv (run du 2026-05-25)

```
métrique,valeur
total_livres,6999
nb_scrappings,7
dernier_scrapping,2026-05-25 12:57:05
prix_moyen,35.07
prix_min,10.0
prix_max,59.99
note_moyenne,2.92
nb_categories,50
livres_note_1,1582
livres_note_2,1372
livres_note_3,1421
livres_note_4,1253
livres_note_5,1371
top_cat_Default,1064
top_cat_Nonfiction,770
top_cat_Sequential Art,525
top_cat_Fiction,455
top_cat_Young Adult,378
```

### 4.6 Logs persistants — pipeline.log (extrait)

```
2026-05-25 13:04:33 | WARNING  | Tentative 1/3 échouée : CHAOS: timeout simulé
2026-05-25 13:04:35 | WARNING  | HTTP 429 reçu — pause de 5s avant retry
2026-05-25 13:04:45 | ERROR    | Abandon après 3 tentatives : ...the-secret_859/index.html
```

### 4.7 Tests unitaires — 21/21 passed

```
platform darwin -- Python 3.12.0, pytest-9.0.3
collected 21 items

tests/test_pipeline.py::TestCleanPrice::test_prix_avec_espaces        PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_chaine_vide         PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_encodage_corrompu   PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_none                PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_normal              PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_sans_symbole        PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_texte_invalide      PASSED
tests/test_pipeline.py::TestCleanPrice::test_prix_virgule_au_lieu_de_point PASSED
tests/test_pipeline.py::TestCleanBooks::test_liste_vide               PASSED
tests/test_pipeline.py::TestCleanBooks::test_livre_complet            PASSED
tests/test_pipeline.py::TestCleanBooks::test_livre_sans_categorie     PASSED
tests/test_pipeline.py::TestCleanBooks::test_livre_sans_prix          PASSED
tests/test_pipeline.py::TestCleanBooks::test_livre_vide               PASSED
tests/test_pipeline.py::TestCleanBooks::test_melange_livres_valides_et_invalides PASSED
tests/test_pipeline.py::TestParsingHTML::test_breadcrumb_trop_court   PASSED
tests/test_pipeline.py::TestParsingHTML::test_classe_css_renommee     PASSED
tests/test_pipeline.py::TestParsingHTML::test_h1_manquant             PASSED
tests/test_pipeline.py::TestParsingHTML::test_html_complet            PASSED
tests/test_pipeline.py::TestParsingHTML::test_html_completement_different PASSED
tests/test_pipeline.py::TestParsingHTML::test_html_vide               PASSED
tests/test_pipeline.py::TestParsingHTML::test_prix_manquant           PASSED

============================== 21 passed in 0.27s ==============================
```

---

## 5. Documentation d'utilisation

### Prérequis
- Docker Desktop installé et lancé
- Git

### Lancer le pipeline

```bash
# Cloner le repo
git clone https://github.com/ninalemoine/data-pipeline-ia.git
cd data-pipeline-ia/session\ 1

# Lancer en arrière-plan (rebuild automatique)
docker compose up -d --build

# Vérifier que le container tourne
docker ps

# Lancer manuellement sans attendre le cron
docker exec python-app python3 /app/main.py

# Suivre les logs en temps réel
docker logs python-app --follow

# Arrêter
docker compose down
```

### Tester la robustesse (Chaos Mode)

```bash
# 30% d'erreurs simulées, backoff 5s pour la démo
docker exec -e CHAOS_MODE=1 -e CHAOS_RATE=0.3 -e HTTP_429_BACKOFF=5 \
    python-app python3 /app/main.py
```

### Lancer les tests unitaires

```bash
cd "session 1"
pip3 install pytest
python3 -m pytest tests/ -v
```

### Variables d'environnement configurables

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DATA_DIR` | `/app/data` | Chemin du dossier de données |
| `LOG_DIR` | `/app/logs` | Chemin du dossier de logs |
| `CHAOS_MODE` | `0` | Activer la simulation d'erreurs (`1` = activé) |
| `CHAOS_RATE` | `0.2` | Taux d'erreurs simulées (0.0 à 1.0) |
| `HTTP_429_BACKOFF` | `60` | Secondes d'attente sur HTTP 429 |

---

## 6. Gestion des erreurs — tableau récapitulatif

| Erreur simulée | Mécanisme de protection | Comportement observé |
|----------------|------------------------|----------------------|
| Timeout réseau | `timeout=10s` + retry 3x | Réessaie automatiquement, log WARNING |
| Connexion refusée | `requests.RequestException` catchée | Réessaie, log ERROR après 3 échecs |
| Erreur SSL | `requests.RequestException` catchée | Réessaie, continue sur le livre suivant |
| HTTP 429 (rate limit) | Détection + backoff configurable | Pause et réessaie |
| Balise HTML manquante | Vérification `if tag else None` | Log WARNING, livre ignoré |
| Prix corrompu (N/A, vide, None) | `try/except ValueError + AttributeError` | Retourne 0.0, log WARNING |
| Clé dict manquante | `.get()` avec valeur par défaut | Valeur par défaut utilisée |
| `books.csv` absent | `if not os.path.exists()` | Log ERROR, analyze() annulée proprement |
| Échec écriture disque | `try/except IOError` | Log ERROR, run annulé proprement |
| Site complètement inaccessible | Vérif `if not book_links` | Log ERROR, pipeline arrêté proprement |
| Erreur inattendue | `except Exception` global + `exc_info=True` | Stack trace loggée, cron ne plante pas |

---

## 7. Sensibilisation RGPD

- **Aucune donnée personnelle** collectée : titres, prix, notes et catégories uniquement
- **Source déclarée** : books.toscrape.com — site public conçu explicitement pour être scrappé
- **Usage responsable** : rate limiting de 0.2s entre chaque requête pour ne pas surcharger le serveur
- **Robots.txt respecté** : books.toscrape.com autorise le scraping dans son robots.txt

---

*Livrable réalisé dans le cadre du module Data Pipelines for AI — Eugenia School, Mai 2026*
*Code source complet : https://github.com/ninalemoine/data-pipeline-ia*
