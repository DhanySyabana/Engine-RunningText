import time
import logging
import requests
from typing import Optional

# Konfigurasi Telegram
TOKEN = "5821659123:AAF_QR8ur3dptVNHSH5MPykGUVgsfRPD82w"
CHAT_ID = "-1002147735635"
TOPIC_ID = 9639


def build_engine_message(engine_name: str, channel_name: str, error_message: str, stacktrace: Optional[str] = None) -> str:
    text = "🚨 ENGINE ERROR 🚨\n"
    text += f"Engine: {engine_name}\n"
    text += f"Channel: {channel_name}\n"
    text += f"Error: {error_message}\n"
    if stacktrace:
        text += "\nStacktrace:\n"
        text += f"{stacktrace}\n"
    text += f"\nWaktu: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    return text


def send_telegram_alert(engine_name: str, channel_name: str, error_message: str, stacktrace: Optional[str] = None) -> None:
    if not TOKEN or not CHAT_ID:
        logging.error('Telegram TOKEN atau CHAT_ID belum dikonfigurasi.')
        return

    apiURL = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': build_engine_message(engine_name, channel_name, error_message, stacktrace),
    }
    if TOPIC_ID:
        payload['message_thread_id'] = TOPIC_ID

    try:
        response = requests.post(apiURL, json=payload, timeout=15)
        response.raise_for_status()
        logging.info('Telegram alert sent successfully')
    except requests.exceptions.RequestException as e:
        logging.error(f'Failed to send Telegram alert: {e}')
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f'Response content: {e.response.text}')
