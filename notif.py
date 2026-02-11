import time
import requests
import logging

# Konfigurasi Telegram
TOKEN = "8213920361:AAEMpyChKoMGb_FHw5QNVI9xdySfjP-yrtk"
CHAT_ID = "-1002147735635"
TOPIC_ID = 9639

def send_telegram_alert(response):
    text = "⚠️ AD VALUE ERROR  ⚠️ \n"
    text += f"\n Detail :"
    text += f"\n {response} \n"
    text += f"\n🗓️: {time.strftime('%d %B %Y %H:%M:%S')}"
    
    apiURL = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    
    payload = {
        'chat_id': CHAT_ID,
        'text': text
    }
    
    if TOPIC_ID:
        payload['message_thread_id'] = TOPIC_ID
    
    try:
        response = requests.post(apiURL, json=payload)
        
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Telegram alert: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response content: {e.response.text}")
    else:
        logging.info(f"Telegram alert sent successfully")
        print("Telegram alert sent successfully!")

if __name__ == "__main__":
    send_telegram_alert()