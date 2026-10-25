import csv
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Permite importar config.py, que está en la carpeta principal
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import URL, HEADERS, COLUMNAS, RAW_DIR, OUT_DIR

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

resp = requests.get(URL, headers=HEADERS, timeout=20)
print("Código de estado:", resp.status_code)
resp.raise_for_status()

# Guardamos el HTML para poder depurar selectores sin volver a pedir la página
(RAW_DIR / "pagina_bs4.html").write_text(resp.text, encoding="utf-8")

soup = BeautifulSoup(resp.text, "html.parser")


def texto(*selectores):
    """Prueba varios selectores y devuelve el primero que funcione."""
    for sel in selectores:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None


datos = {
    "titulo": texto("h1.ui-pdp-title", "h1"),
    "precio": texto(
        "div.ui-pdp-price__second-line span.andes-money-amount__fraction",
        "span.andes-money-amount__fraction",
    ),
    "vendedor": texto(
        "div.ui-pdp-seller__header__title",
        "a.ui-pdp-media__action span",
    ),
    "calificacion": texto("span.ui-pdp-review__rating"),
    "num_opiniones": texto("span.ui-pdp-review__amount"),
    "url": URL,
}

print(datos)

with open(OUT_DIR / "bs4_resultado.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNAS)
    writer.writeheader()
    writer.writerow(datos)

print("CSV guardado en", OUT_DIR / "bs4_resultado.csv")