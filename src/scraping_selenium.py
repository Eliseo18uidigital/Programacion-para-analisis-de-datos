import csv
import re
import sys
import time
import traceback
from pathlib import Path

print("Iniciando script...")

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import URL, COLUMNAS, RAW_DIR, OUT_DIR

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEL_RESENA = "article.ui-review-capability-comments__comment"
driver = None


def primer_texto(selectores):
    for sel in selectores:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            t = el.text.strip()
            if t:
                return t
    return None


def buscar_vendedor():
    descartar = [
        "medios de pago", "productos del vendedor", "vendido por", "ver más",
        "ver todos", "seguir", "ventas", "mercadolíder", "mercadolider",
        "ir a la tienda", "tienda oficial", "reputación", "reputacion",
        "calificaciones", "atiende", "brinda", "ubicación", "ubicacion",
    ]
    candidatos = []
    for el in driver.find_elements(By.CSS_SELECTOR, "[class*='seller']"):
        for linea in el.text.split("\n"):
            linea = linea.strip()
            if 2 < len(linea) < 60 and not any(d in linea.lower() for d in descartar):
                candidatos.append(linea)
    print("Candidatos a vendedor:", candidatos[:10])
    return candidatos[0] if candidatos else None


def scroll_gradual(pasos=8, pausa=0.8):
    for _ in range(pasos):
        driver.execute_script("window.scrollBy(0, 700);")
        time.sleep(pausa)


def buscar_tarjetas():
    selectores = [
        SEL_RESENA,
        "div.ui-review-capability-comments__comment",
        "[class*='comments__comment']",
        "[class*='review-capability-comments'] article",
    ]
    for sel in selectores:
        textos = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, sel)
                  if e.text.strip()]
        if textos:
            print("Selector que funcionó:", sel)
            return textos
    return []


def cargar_mas_en_marco(max_clicks=15):
    previo = -1
    for _ in range(max_clicks):
        n = len(driver.find_elements(By.CSS_SELECTOR, SEL_RESENA))
        if n == previo:
            break
        previo = n
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        botones = driver.find_elements(
            By.XPATH,
            "//button[contains(., 'Mostrar más') or contains(., 'Ver más') "
            "or contains(., 'Cargar más')]",
        )
        if not botones:
            break
        try:
            driver.execute_script("arguments[0].click();", botones[0])
        except Exception:
            break
        time.sleep(2)


def clases_relacionadas():
    return driver.execute_script(
        """
        const s = new Set();
        document.querySelectorAll('[class]').forEach(e => {
            e.classList.forEach(c => {
                if (/comment|review|opinion/i.test(c)) s.add(c);
            });
        });
        return Array.from(s);
        """
    )


def main():
    global driver

    opciones = webdriver.ChromeOptions()
    opciones.add_argument("--lang=es-CO")
    opciones.add_argument("--window-size=1366,900")
    opciones.add_argument("--no-first-run")
    opciones.add_argument("--no-default-browser-check")
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    # Mantiene Chrome abierto aunque el script termine o falle
    opciones.add_experimental_option("detach", True)

    print("Abriendo Chrome (la primera vez puede tardar)...")
    driver = webdriver.Chrome(options=opciones)
    print("Chrome abierto. Cargando Mercado Libre...")
    driver.get(URL)

    print("\nSe abrió Mercado Libre. Si aparece registro, login o aviso:")
    print("  - Resuélvelo tú mismo en la ventana de Chrome.")
    print("  - Si te manda al inicio, pega el enlace del producto en la barra.")
    print("  - Cuando veas la ficha de la guitarra, vuelve aquí.")
    input("Presiona Enter para continuar con la extracción...")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
        )
    except TimeoutException:
        driver.save_screenshot(str(RAW_DIR / "selenium_bloqueo.png"))
        print("Aún no se detecta el título del producto.")

    time.sleep(2)

    # ---------- Datos principales ----------
    num_op = primer_texto(["span.ui-pdp-review__amount"])
    datos = {
        "titulo": primer_texto(["h1.ui-pdp-title", "h1"]),
        "precio": primer_texto([
            "div.ui-pdp-price__second-line span.andes-money-amount__fraction",
            "span.andes-money-amount__fraction",
        ]),
        "vendedor": buscar_vendedor(),
        "calificacion": primer_texto(["span.ui-pdp-review__rating"]),
        "num_opiniones": re.sub(r"[^\d]", "", num_op) if num_op else None,
        "url": URL,
    }
    print(datos)

    with open(OUT_DIR / "selenium_resultado.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS)
        writer.writeheader()
        writer.writerow(datos)
    print("Guardado selenium_resultado.csv")

    # ---------- Reseñas ----------
    scroll_gradual()

    try:
        boton = driver.find_element(
            By.XPATH,
            "//a[contains(., 'Ver todas') and contains(., 'opiniones')] | "
            "//button[contains(., 'Ver todas') and contains(., 'opiniones')] | "
            "//a[contains(., 'Mostrar todas')] | //button[contains(., 'Mostrar todas')]",
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", boton)
        time.sleep(1)
        boton.click()
        time.sleep(3)
        scroll_gradual(pasos=5)
        print("Se hizo clic en el botón de opiniones.")
    except Exception:
        print("No se encontró botón de 'ver todas'; se usan las opiniones visibles.")

    resenas = buscar_tarjetas()

    if not resenas:
        total_marcos = len(driver.find_elements(By.TAG_NAME, "iframe"))
        print("Iframes en la página:", total_marcos)
        for i in range(total_marcos):
            driver.switch_to.default_content()
            marcos = driver.find_elements(By.TAG_NAME, "iframe")
            try:
                driver.switch_to.frame(marcos[i])
            except Exception:
                continue
            cargar_mas_en_marco()
            resenas = buscar_tarjetas()
            if resenas:
                break
        driver.switch_to.default_content()

    print(f"Reseñas encontradas: {len(resenas)}")

    if not resenas:
        print("\n--- DIAGNÓSTICO (cópialo y pásamelo) ---")
        for c in clases_relacionadas():
            print("  ", c)

    with open(OUT_DIR / "selenium_resenas.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["n", "texto_resena"])
        for i, r in enumerate(resenas, start=1):
            writer.writerow([i, r.replace("\n", " | ")])
    print("Guardado selenium_resenas.csv")

    (RAW_DIR / "pagina_selenium.html").write_text(driver.page_source, encoding="utf-8")
    driver.save_screenshot(str(RAW_DIR / "selenium_final.png"))
    print("\nListo. Archivos guardados en data\\processed y data\\raw.")


try:
    main()
except Exception:
    print("\n=== OCURRIÓ UN ERROR (cópialo y pásamelo) ===")
    traceback.print_exc()
finally:
    input("\nPresiona Enter para terminar y cerrar Chrome...")
    try:
        if driver:
            driver.quit()
    except Exception:
        pass