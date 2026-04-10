# 🔔 Price Monitor — Alertas automáticas de precio

Script Python que monitoriza el precio de cualquier producto online y envía 
un email automático cuando baja del umbral que configures.

## ¿Qué problema resuelve?

Dejaste de comprar algo porque era caro, y cuando bajó de precio ya no te 
enteraste. Este script lo vigila por ti y te avisa en el momento.

## Demostración

[Aquí pon una captura del email recibido o un GIF de la consola]

## Características

- ✅ Funciona con cualquier web (PCComponentes, Amazon, MediaMarkt...)
- ✅ Email HTML con diseño profesional
- ✅ Configuración sin tocar código (solo editar config.yaml)
- ✅ Log completo de todas las comprobaciones
- ✅ Comprobaciones automáticas cada X horas

## Instalación

\```bash
git clone https://github.com/tu-usuario/price-monitor
cd price-monitor
pip install -r requirements.txt
\```

## Configuración

Edita `config.yaml` con tu URL, precio umbral y credenciales de email.
Ver instrucciones de App Password en el archivo.

## Uso

\```bash
python monitor.py
\```

## Tecnologías

Python 3.11 · requests · BeautifulSoup4 · smtplib · PyYAML · schedule

## ¿Quieres algo similar para tu negocio?

Puedo adaptarlo a tu caso concreto. Contacto: [tu perfil de Malt]