# =============================================================================
# monitor.py — Price Monitor con alertas por email
# Autor: tu nombre
# Descripción: Monitoriza el precio de un producto web y envía un email
#              automático cuando baja del umbral configurado.
# =============================================================================

import requests
import smtplib
import yaml
import schedule
import time
import logging
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# -----------------------------------------------------------------------------
# BLOQUE 1: Configuración del logger
# El logger guarda un historial de todo lo que hace el script en la consola.
# Así sabes qué pasó y cuándo, sin tener que añadir prints por todos lados.
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# BLOQUE 2: Cargar configuración desde config.yaml
# Separar config del código es una práctica profesional clave.
# El cliente puede cambiar URL o email sin tocar Python.
# -----------------------------------------------------------------------------
def load_config(path: str = 'config.yaml') -> dict:
    """
    Lee el archivo config.yaml y devuelve un diccionario con los valores.
    Si el archivo no existe o tiene errores, lanza una excepción clara.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuración cargada desde '{path}'")
        return config
    except FileNotFoundError:
        logger.error(f"No se encontró '{path}'. Asegúrate de que existe.")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error al parsear el YAML: {e}")
        raise


# -----------------------------------------------------------------------------
# BLOQUE 3: Scraper — extrae el precio de la página web
# Aquí está la lógica de web scraping.
# IMPORTANTE: cada web estructura su HTML diferente, así que esta función
# tiene un sistema de selectores CSS que se pueden adaptar fácilmente.
# -----------------------------------------------------------------------------
def get_price(url: str) -> float | None:
    """
    Hace una petición GET a la URL y extrae el precio del producto.
    Devuelve el precio como float, o None si no lo encuentra.
    """
    # Headers que simulan un navegador real.
    # Sin esto, muchas webs bloquean las peticiones automáticas.
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'es-ES,es;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # lanza excepción si status != 200
    except requests.RequestException as e:
        logger.error(f"Error al acceder a la URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # -------------------------------------------------------------------------
    # SELECTORES CSS — Lista de posibles lugares donde puede estar el precio.
    # BeautifulSoup busca el primero que exista en la página.
    # Para adaptar a otra web: inspecciona el elemento del precio (clic derecho
    # → Inspeccionar) y añade su selector aquí.
    # -------------------------------------------------------------------------
    price_selectors = [
        {'class': 'price'},                          # genérico
        {'class': 'pvpr-price'},                     # PCComponentes
        {'id': 'priceblock_ourprice'},               # Amazon (legacy)
        {'class': 'a-price-whole'},                  # Amazon (actual)
        {'class': 'precio'},                         # sitios ES genéricos
        {'itemprop': 'price'},                       # schema.org estándar
        {'data-testid': 'price-display'},            # algunos e-commerce
    ]

    for selector in price_selectors:
        element = soup.find(attrs=selector)
        if element:
            # Limpiamos el texto: quitamos €, espacios, comas → float
            raw = element.get_text(strip=True)
            price = parse_price(raw)
            if price is not None:
                logger.info(f"Precio encontrado: {price:.2f} € (selector: {selector})")
                return price

    # Si ningún selector funcionó, intentamos buscar por meta tag (schema.org)
    meta = soup.find('meta', {'itemprop': 'price'})
    if meta and meta.get('content'):
        price = parse_price(meta['content'])
        if price is not None:
            logger.info(f"Precio encontrado en meta tag: {price:.2f} €")
            return price

    logger.warning("No se pudo extraer el precio. Revisa los selectores para esta web.")
    return None


def parse_price(raw: str) -> float | None:
    """
    Convierte un string de precio a float.
    Maneja formatos: '249,99 €', '249.99', '1.249,99€', etc.
    """
    # Quitamos todo excepto dígitos, puntos y comas
    clean = ''.join(c for c in raw if c.isdigit() or c in '.,')  
    if not clean:
        return None
    # Formato europeo: 1.249,99 → 1249.99
    if ',' in clean and '.' in clean:
        clean = clean.replace('.', '').replace(',', '.')
    elif ',' in clean:
        clean = clean.replace(',', '.')
    try:
        return float(clean)
    except ValueError:
        return None


# -----------------------------------------------------------------------------
# BLOQUE 4: Email — envía la alerta cuando el precio baja
# Usa smtplib (librería estándar de Python, no necesita instalarse).
# El email es HTML para que se vea bien en cualquier cliente de correo.
# -----------------------------------------------------------------------------
def send_alert_email(config: dict, current_price: float) -> bool:
    """
    Envía un email HTML con la alerta de bajada de precio.
    Devuelve True si se envió correctamente, False si hubo error.
    """
    # Construimos el mensaje con MIME (estándar de emails)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔔 Alerta de precio: {config['product_name']} — {current_price:.2f} €"
    msg['From'] = config['sender_email']
    msg['To'] = config['receiver_email']

    # Cuerpo del email en HTML — esto es lo que ve el cliente
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #0070f3; padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="color: white; margin: 0;">🔔 Alerta de Precio</h1>
        </div>
        <div style="border: 1px solid #e0e0e0; padding: 24px; border-radius: 0 0 8px 8px;">
            <h2 style="color: #333;">{config['product_name']}</h2>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="background: #f5f5f5;">
                    <td style="padding: 12px; font-weight: bold;">Precio actual</td>
                    <td style="padding: 12px; color: #22c55e; font-size: 24px; font-weight: bold;">
                        {current_price:.2f} €
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: bold;">Tu umbral</td>
                    <td style="padding: 12px; color: #666;">{config['price_threshold']:.2f} €</td>
                </tr>
                <tr style="background: #f5f5f5;">
                    <td style="padding: 12px; font-weight: bold;">Ahorro</td>
                    <td style="padding: 12px; color: #0070f3; font-weight: bold;">
                        {config['price_threshold'] - current_price:.2f} € por debajo de tu umbral
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: bold;">Detectado</td>
                    <td style="padding: 12px; color: #666;">{datetime.now().strftime('%d/%m/%Y a las %H:%M')}</td>
                </tr>
            </table>
            <a href="{config['product_url']}"
               style="display: inline-block; background: #0070f3; color: white;
                      padding: 12px 24px; border-radius: 6px; text-decoration: none;
                      font-weight: bold; margin-top: 8px;">
                Ver producto →
            </a>
            <p style="color: #999; font-size: 12px; margin-top: 24px;">
                Este email fue generado automáticamente por Price Monitor.
            </p>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

    try:
        # Conexión segura al servidor SMTP de Gmail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(config['sender_email'], config['sender_password'])
            server.sendmail(
                config['sender_email'],
                config['receiver_email'],
                msg.as_string()
            )
        logger.info(f"Email de alerta enviado a {config['receiver_email']}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Error de autenticación. Revisa el email y la App Password en config.yaml")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"Error al enviar email: {e}")
        return False


# -----------------------------------------------------------------------------
# BLOQUE 5: Lógica principal — une todo
# Esta función se ejecuta cada X horas según el config.
# Compara el precio actual con el umbral y decide si mandar alerta.
# -----------------------------------------------------------------------------
def check_price_and_alert(config: dict) -> None:
    """
    Función principal que se ejecuta en cada ciclo de monitorización.
    1. Obtiene el precio actual
    2. Lo compara con el umbral
    3. Si baja del umbral, manda el email
    """
    logger.info(f"--- Comprobando precio de: {config['product_name']} ---")
    logger.info(f"URL: {config['product_url']}")

    current_price = get_price(config['product_url'])

    if current_price is None:
        logger.warning("No se pudo obtener el precio en esta comprobación. Se reintentará en el próximo ciclo.")
        return

    logger.info(f"Precio actual: {current_price:.2f} € | Umbral: {config['price_threshold']:.2f} €")

    if current_price <= config['price_threshold']:
        logger.info("✅ ¡PRECIO POR DEBAJO DEL UMBRAL! Enviando alerta...")
        send_alert_email(config, current_price)
    else:
        diff = current_price - config['price_threshold']
        logger.info(f"❌ Precio aún alto. Faltan {diff:.2f} € para activar la alerta.")


def main():
    """
    Punto de entrada del script.
    Carga la config, ejecuta una comprobación inicial inmediata,
    y luego programa comprobaciones periódicas.
    """
    logger.info("=" * 60)
    logger.info("  Price Monitor — Iniciando")
    logger.info("=" * 60)

    config = load_config()

    # Comprobación inmediata al arrancar (no espera el primer intervalo)
    check_price_and_alert(config)

    # Programar comprobaciones periódicas según config
    interval = config.get('check_interval_hours', 6)
    schedule.every(interval).hours.do(check_price_and_alert, config=config)
    logger.info(f"Programado: comprobación cada {interval} horas.")
    logger.info("Presiona Ctrl+C para detener.")

    # Bucle infinito que mantiene el script corriendo
    while True:
        schedule.run_pending()
        time.sleep(60)  # revisa cada minuto si hay tareas pendientes


# Punto de entrada estándar de Python
# Solo ejecuta main() si el script se lanza directamente (no si se importa)
if __name__ == '__main__':
    main()