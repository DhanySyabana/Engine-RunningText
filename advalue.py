from pymongo import UpdateOne
from constants import properties
from notif import send_telegram_alert
from modules.mongo import db, GetOCRResult
import threading
import requests
import time
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("ADVALUE_URL", "https://siputra-api.kurasi.media/streams/rumus-ad-value")
zero_value_counters = {}
def calculatePrice(d, channel):
    dt = d['time'].strftime("%Y-%m-%dT%H:%M:%S")
    durasi = max(round(d['duration']), 1)
    body = {
            "data": {
                "nama_media": channel,
                "publish_date": dt,
                "durasi_video": durasi,
            }
        }
    
    response = tryRequest(body, channel, dt, durasi)
    if response is None:
        return
    d.update({"ad_value": response['ad_value']})
    

def tryRequest(body, channel,dt, durasi, tries=5):
    global zero_value_counters
    
    while tries > 0:
        try:
            response = requests.post(URL, json=body)
            response = response.json()

            if channel not in zero_value_counters:
                zero_value_counters[channel] = 0

            if response['ad_value'] == 0:
                zero_value_counters[channel] += 1
                
                if zero_value_counters[channel] >= 3:
                    alert_message = (
                        f"Channel : {channel}\n"
                        f"Publish Date: {dt}\n"
                        f"Durasi Video: {durasi} detik\n"
                        f"AD Value : {response['ad_value']}"
                    )
                    
                    send_telegram_alert(alert_message)

                    zero_value_counters[channel] = 0
            else:

                zero_value_counters[channel] = 0
            
            return response
        except Exception as e:
            print("Error: ", e)
            # traceback.print_exc()
            send_telegram_alert(e)
            if 'response' in locals():
                print(response.text)
            print(body)
            tries -= 1
    return None
    
def calculatePriceBatched(data, channel):
    batch = []
    for d in data:
        calculatePrice(d, channel)
        batch.append(UpdateOne({"_id": d['_id']}, {"$set": d}))
    if len(batch) > 0:
        print(db.result_ocr.bulk_write(batch))

def channelThread(channel):
    total = 999
    while total > 0:
        data, total, _ = GetOCRResult(channels=[channel], is_calculated=False)
        calculatePriceBatched(data, channel)
        

if __name__ == '__main__':
    tv = list(properties.tv.keys())
    # tv = [tv[1]]
    threads = []
    for t in tv:
        th = threading.Thread(target=channelThread, args=(t,))   
        th.start()
        threads.append(th)
    for t in threads:
        t.join()