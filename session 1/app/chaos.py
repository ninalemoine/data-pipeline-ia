"""
Module de simulation d'erreurs pour tester la robustesse du pipeline.

Activation : définir CHAOS_MODE=1 dans les variables d'environnement.
Taux d'erreur configurable via CHAOS_RATE (défaut : 0.2 = 20%).

Exemples :
  CHAOS_MODE=1 python3 /app/main.py
  CHAOS_MODE=1 CHAOS_RATE=0.5 python3 /app/main.py
"""
import os
import random
import requests
from logger import get_logger

logger = get_logger(__name__)

CHAOS_MODE = os.environ.get("CHAOS_MODE", "0") == "1"
CHAOS_RATE = float(os.environ.get("CHAOS_RATE", "0.2"))

if CHAOS_MODE:
    logger.warning(f"⚠ CHAOS MODE ACTIVÉ — taux d'erreur simulé : {int(CHAOS_RATE * 100)}%")


def maybe_raise_network_error(url: str) -> None:
    """Simule une erreur réseau aléatoire (timeout, connexion refusée)."""
    if CHAOS_MODE and random.random() < CHAOS_RATE:
        error_type = random.choice([
            requests.exceptions.Timeout("CHAOS: timeout simulé"),
            requests.exceptions.ConnectionError("CHAOS: connexion refusée simulée"),
            requests.exceptions.SSLError("CHAOS: erreur SSL simulée"),
        ])
        logger.warning(f"CHAOS: erreur réseau injectée sur {url}")
        raise error_type


def maybe_corrupt_price(price: str) -> str:
    """Simule un prix corrompu (encodage cassé, caractère inattendu)."""
    if CHAOS_MODE and random.random() < CHAOS_RATE:
        corrupted = random.choice(["N/A", "", "??£", "None", "abc"])
        logger.warning(f"CHAOS: prix '{price}' corrompu en '{corrupted}'")
        return corrupted
    return price


def maybe_drop_field() -> bool:
    """Simule un champ HTML manquant (retourne True = simuler None)."""
    if CHAOS_MODE and random.random() < CHAOS_RATE:
        logger.warning("CHAOS: champ HTML manquant simulé")
        return True
    return False


def maybe_raise_http_429() -> bool:
    """Simule une réponse HTTP 429 (rate limit)."""
    if CHAOS_MODE and random.random() < CHAOS_RATE:
        logger.warning("CHAOS: HTTP 429 simulé")
        return True
    return False
