"""
Engine.py — Master Engine (Sequential Loop)
============================================
Menggantikan 11 file Engine_*.py terpisah.
Semua channel diproses secara SEQUENTIAL dalam 1 proses Python,
sehingga model AI hanya dimuat SEKALI dan GPU tidak berkonflik.

Cara menjalankan:
    python Engine.py

Cara menonaktifkan channel tertentu:
    Comment/hapus entry channel yang bersangkutan di CHANNELS list.
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta

import torch

from modules.cropper import cropAndOcr
from modules.mongo import (
    SaveResults,
    addNewWatchLog,
    getLastProcessedVideo,
    updateWatchLogStatus,
)
from modules.routines import deleteExpiredFile
from modules.watcher import getNextUnprocessVideo
from constants import properties
from SendTelegram.Enginenotif import send_telegram_alert

# =============================================================================
# KONFIGURASI CHANNEL
# Tambah atau comment channel sesuai kebutuhan.
# Format: ('nama_channel_di_db', 'path_folder_rekaman')
# =============================================================================
CHANNELS = [
    ('cnn',           'D:\\Medmon\\Raw-data\\CNN'),
    ('kompastv',      'D:\\Medmon\\Raw-data\\KOMPAS'),
    # ('metrotv',       '/home/comvis/siputri/METROTVSTB'),
]

# Jeda antar satu full-loop (semua channel selesai diproses sekali putaran)
LOOP_SLEEP_SECONDS = 5

# =============================================================================
# CORE PROCESSING FUNCTION
# =============================================================================

def process_channel(channel: str, channel_path: str) -> None:
    """
    Memproses satu video berikutnya untuk channel yang diberikan.
    Jika tidak ada video baru, fungsi ini langsung return tanpa melakukan apa-apa.
    """
    log_id = None
    tries  = 0

    try:
        last = getLastProcessedVideo(channel)
        print(f"[{channel.upper()}] last record: {last}")

        # --- Tentukan titik awal pencarian video ---
        if last is None:
            # Pertama kali dijalankan: mulai dari awal hari 3 hari lalu
            base = datetime.today() - timedelta(days=3)
            last_time = datetime.strptime(base.strftime('%Y%m%d') + '000000', '%Y%m%d%H%M%S')
        else:
            tries = last.get('tries') or 0
            if last['status'] != 'COMPLETED':
                # Proses sebelumnya gagal — tandai FAILED jika belum
                if last['status'] != 'FAILED':
                    updateWatchLogStatus(last['_id'], 'FAILED')

                if tries <= 15:
                    # Retry: mundur 2 menit agar file yang sama dicoba ulang
                    last_time = last['time'] - timedelta(minutes=2)
                else:
                    # Sudah terlalu banyak retry — lewati file ini
                    last_time = last['time']
                    tries = 0
            else:
                last_time = last['time']
                tries = 0

        # --- Cari video berikutnya ---
        file_path, timestamps = getNextUnprocessVideo(channel_path, last_time, channel)

        if file_path is None or timestamps is None:
            print(f"[{channel.upper()}] Tidak ada video baru. Skip.")
            return

        # --- Proses video ---
        print(f"[{channel.upper()}] Memproses: {file_path}")
        print(f"[{channel.upper()}] Properties: {properties.tv[channel]}")

        log_id = addNewWatchLog(timestamps, channel, datetime.now(), tries)

        res = cropAndOcr(
            os.path.join(channel_path, file_path),
            timestamps,
            **properties.tv[channel],
            logId=log_id,
            folderOutput=channel,
        )

        SaveResults(res, channel, properties.tv[channel]['alias'])
        torch.cuda.empty_cache()
        updateWatchLogStatus(log_id, 'COMPLETED')

        print(f"[{channel.upper()}] Selesai: {file_path}")

    except Exception as e:
        print(f"[{channel.upper()}] ERROR: {e}")
        print(traceback.format_exc())
        send_telegram_alert(engine_name="Engine_Fasttrack", channel_name=channel, error_message=str(e), stacktrace=traceback.format_exc())
        if log_id is not None:
            updateWatchLogStatus(log_id, 'FAILED', repr(e), tries + 1)


def delete_routine() -> None:
    """Bersihkan file-file yang sudah expired."""
    try:
        deleteExpiredFile()
    except Exception as e:
        print(f"[DELETE_ROUTINE] ERROR: {e}")
        print(traceback.format_exc())
        send_telegram_alert(engine_name="Engine_Fasttrack", channel_name="DELETE_ROUTINE", error_message=str(e), stacktrace=traceback.format_exc())


# =============================================================================
# MAIN LOOP
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  Engine #1 — Sequential Channel Processor")
    print(f"  Jumlah channel aktif : {len(CHANNELS)}")
    print(f"  Loop sleep           : {LOOP_SLEEP_SECONDS}s")
    print("=" * 60)

    loop_count = 0
    while True:
        loop_count += 1
        print(f"\n{'='*60}")
        print(f"  Loop #{loop_count}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        for channel, channel_path in CHANNELS:
            process_channel(channel, channel_path)

        # Jalankan delete routine setiap loop selesai
        delete_routine()

        print(f"\n[ENGINE] Semua channel selesai diproses. Menunggu {LOOP_SLEEP_SECONDS}s...")
        time.sleep(LOOP_SLEEP_SECONDS)
