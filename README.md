# Data Pipeline for IA

Pipeline de scraping et de traitement de données de livres depuis [books.toscrape.com](https://books.toscrape.com).

## Description

Ce projet scrape automatiquement les informations de 1000 livres (50 pages) depuis le site books.toscrape.com, nettoie les données et les exporte dans un fichier CSV.

## Structure du projet

```
Data Pipeline for IA/
├── app/
│   ├── main.py        # Point d'entrée principal du pipeline
│   ├── scraper.py     # Récupération des données depuis le site
│   └── transform.py   # Nettoyage et transformation des données
├── data/
│   └── books.csv      # Fichier de sortie généré
└── README.md
```

## Données collectées

Pour chaque livre :
- **title** — titre du livre
- **price** — prix en livres sterling (£)
- **rating** — note de 1 à 5
- **category** — catégorie du livre
- **scraping_date** — date et heure du scraping

## Installation

```bash
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install requests beautifulsoup4
```

## Utilisation

```bash
python app/main.py
```

Le fichier `data/books.csv` est créé (ou mis à jour) à la fin de l'exécution.

## Fonctionnement

1. **Scraper** (`scraper.py`) — génère les liens des 50 pages, extrait les liens de chaque livre, puis scrape titre, prix, note et catégorie
2. **Transform** (`transform.py`) — nettoie le prix (supprime le symbole £, convertit en float), filtre les entrées vides
3. **Main** (`main.py`) — orchestre le pipeline, fusionne avec les données existantes pour éviter les doublons, exporte en CSV

## Schéma du pipeline

Le schéma du pipeline est disponible dans [`docs/pipeline_schema.pdf`](docs/pipeline_schema.pdf).

## Ouvrir le CSV dans Excel

Excel en locale française utilise le point-virgule comme séparateur. Pour ouvrir correctement le fichier :
- **Option 1** : Dans Excel, utiliser *Données > À partir d'un fichier texte/CSV* et choisir la virgule comme délimiteur
- **Option 2** : Modifier `main.py` ligne 56 et ajouter `delimiter=";"` dans `csv.DictWriter`
