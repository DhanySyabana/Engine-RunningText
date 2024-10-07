

import os
import sys
from moviepy import editor
from modules.cropper import cropAndOcr
from constants import properties
import threading
import psutil
import time


def display_cpu():
    global running

    running = True

    currentProcess = psutil.Process()

    print(psutil.cpu_count())
    # start loop
    while running:
        print(currentProcess.cpu_percent(interval=1), end='% ')
        print(currentProcess.memory_percent(), end='% ')
        print(currentProcess.memory_info().rss / 1024 / 1024, end='MB\n')
        sys.stdout.flush() 

def start():
    global t

    # create thread and start it
    t = threading.Thread(target=display_cpu)
    t.start()
    
def stop():
    global running
    global t
    global start_time

    # use `running` to stop loop in thread so thread will end
    running = False

    # wait for thread's end
    t.join()
    print("Elapsed time: ", time.time() - start_time)

start_time = time.time()

if __name__ == '__main__':
    #cropAndOcrv2('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right']) 
    #cropAndOcrv2('videos/1. Metro TV - 22072024 ( 06.50 ).mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'])
    channel = 'rcti'
    #cropAndOcrv2('videos/2. Kompas TV - 22072024 ( 06.58 ).mp4', properties.tv[channel]['type'], properties.tv[channel]['top'], properties.tv[channel]['left'], properties.tv[channel]['bottom'], properties.tv[channel]['right'], properties.tv[channel]['threshold'])
    #cropAndOcrv2('videos/11. Trans 7 - 22072024 ( 14.19 ).mp4', properties.tv[channel]['type'], properties.tv[channel]['top'], properties.tv[channel]['left'], properties.tv[channel]['bottom'], properties.tv[channel]['right'], properties.tv[channel]['threshold'])
    #cropAndOcrv2('videos/6. CNN - 22072024 ( 06.50 ).mp4', properties.tv[channel]['type'], properties.tv[channel]['top'], properties.tv[channel]['left'], properties.tv[channel]['bottom'], properties.tv[channel]['right'], properties.tv[channel]['threshold'])
    #cropAndOcrv2('videos/3. Berita Satu TV - 22072024 ( 08.28 ).mp4', properties.tv[channel]['type'], properties.tv[channel]['top'], properties.tv[channel]['left'], properties.tv[channel]['bottom'], properties.tv[channel]['right'], properties.tv[channel]['threshold'])
    #cropAndOcrv2('videos/4. IDX Channel - 22072024 ( 07.00 - Tidak ada Jam pada Video ).mp4', properties.tv[channel]['type'], properties.tv[channel]['top'], properties.tv[channel]['left'], properties.tv[channel]['bottom'], properties.tv[channel]['right'], properties.tv[channel]['threshold'])
    #cropAndOcrv2('videos/5. iNews TV - 22072024 ( 08.57 ).mp4', properties.tv[channel]['type'], properties.tv[channel]['top'], properties.tv[channel]['left'], properties.tv[channel]['bottom'], properties.tv[channel]['right'], properties.tv[channel]['threshold'])
    start()
    try:

        t1 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t1"))
        t2 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t2"))

        t3 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t2"))

        t4 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t2"))
        t5 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t1"))
        t6 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t2"))

        t7 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t2"))

        t8 = threading.Thread(target=cropAndOcr, args=('videos/Metro TV 18 Juli 2024.mp4', properties.tv['metrotv']['type'], properties.tv['metrotv']['top'], properties.tv['metrotv']['left'], properties.tv['metrotv']['bottom'], properties.tv['metrotv']['right'], properties.tv['metrotv']['threshold'], "t2"))
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
        t1.join()
        t2.join()
        t3.join()
        t4.join()
        t5.join()
        t6.join()
        t7.join()
        t8.join()
    finally:
        stop()

    #editor = editor.VideoFileClip('videos/10. RCTI - 22072024 ( 11.26 ).mp4')
    #editor = editor.subclip(5*60 + 15, 5*60 + 15 + 2*60)
    #editor.write_videofile('videos/10.mp4')
