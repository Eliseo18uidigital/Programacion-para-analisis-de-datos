from pathlib import Path

# URL limpia (sin los parámetros de rastreo después del #)
URL = (
    "https://www.mercadolibre.com.co/"
    "guitarra-electrica-stratocaster-ibrah-amplif-accesorios-color-negro-"
    "material-del-diapason-madera-de-calidad-orientacion-de-la-mano-diestro/"
    "p/MCO28364954"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}

COLUMNAS = ["titulo", "precio", "vendedor", "calificacion", "num_opiniones", "url"]

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUT_DIR = BASE_DIR / "data" / "processed"