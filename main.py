

import os
import sys
from cv2.gapi.streaming import timestamp
from moviepy import editor
from modules.cropper import cropAndOcr
from modules.mongo import SaveResults, addNewWatchLog, getLastProcessedVideo, updateWatchLogStatus
from modules.routines import deleteExpiredFile
from modules.watcher import getNextUnprocessVideo
from constants import properties
from datetime import datetime, timedelta
import threading
import psutil
import time
import shutil
import traceback


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
def run(channel, channelPath):
    i = 0
    while True:
        id = None
        try:
            last = getLastProcessedVideo(channel)

            print("last : ", last)

            
            if last is None:
                lastTime = datetime.today() - timedelta(days=1)
                today = lastTime.strftime('%Y%m%d')
                today_morning = today + "000000"
                lastTime = datetime.strptime(today_morning, '%Y%m%d%H%M%S')
            else:
                if last['status'] != 'COMPLETED':
                    #that means previous run is failed
                    s = updateWatchLogStatus(last["_id"], "FAILED")
                    print('Last s: ', last)
                    print('S: ', s)
                    lastTime = last["time"] - timedelta(minutes=2)
                else:
                    lastTime = last['time']
            print(lastTime)

            filePath, timestamps = getNextUnprocessVideo(channelPath, lastTime, channel )
            print(filePath,timestamps)

            print(channelPath+ '/' +filePath)

            if filePath is None or timestamps is None:
                time.sleep(60)
                continue
            #shutil.copy(channelPath+ '/' + filePath, 'temp/' )
            id = addNewWatchLog(timestamps, channel, datetime.now())
            res = cropAndOcr(channelPath+ '/' + filePath, timestamps, **properties.tv[channel], logId=id, folderOutput=f'output/{channel}' )

            sr = SaveResults(res, channel)

            print(sr)
           
            updateWatchLogStatus(id, 'COMPLETED')
            i+=1
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            if id is not None:
                updateWatchLogStatus(id, 'FAILED', repr(e) )
            break

def deleteRoutine():
    while True:
        try:
            deleteExpiredFile()
        except Exception as e:
            print(e)
            print(traceback.format_exc)
        time.sleep(10*60)

if __name__ == '__main__':
    metroThread = threading.Thread(target=run, args=('metrotv', '/home/comvis/siputri/METROTVSTREAMING'))
    kompasThread = threading.Thread(target=run, args=('kompastv', '/home/comvis/siputri/KOMPASSTREAMING'))
    cnnThread = threading.Thread(target=run, args=('cnn', '/home/comvis/siputri/CNNSTREAMING'))
    rctiThread = threading.Thread(target=run, args= ('rcti', '/home/comvis/remote1/RCTISTREAMING'))
    #trans7Thread = threading.Thread(target=run, args=('trans7', '/home/comvis/remote1/TRANS7STREAMING'))
    berita1Thread = threading.Thread(target=run, args=('beritasatu', '/home/comvis/remote1/BERITASATUSTREAMING'))
    idxThread = threading.Thread(target=run, args=('idxchannel', '/home/comvis/siputri/IDXSTREAMING'))
    inewsThread = threading.Thread(target=run, args=('inewstv', '/home/comvis/remote1/INEWSSTREAMING'))
    nusataraThread = threading.Thread(target=run, args=('nusantaratv', '/home/comvis/remote1/NUSANTARATVSTREAMING'))
    mncThread = threading.Thread(target=run, args=('mnctv', '/home/comvis/remote2/MNCSTREAMING'))
    tvoneThread = threading.Thread(target=run, args=('tvone','/home/comvis/siputri/TVONESTREAMING'))
    tvriThread = threading.Thread(target=run, args=('tvri', '/home/comvis/remote2/TVRISTREAMING'))
    deleteThread = threading.Thread(target=deleteRoutine)

    metroThread.start()
    kompasThread.start()
    cnnThread.start()
    rctiThread.start() 
    #trans7Thread.start() 
    berita1Thread.start()
    idxThread.start()
    inewsThread.start()
    nusataraThread.start()
    #mncThread.start()
    #tvoneThread.start()
    #tvriThread.start()
    #deleteThread.start()

    metroThread.join()
    kompasThread.join()
    cnnThread.join()
    rctiThread.join() 
    #trans7Thread.join() 
    berita1Thread.join()
    idxThread.join()
    inewsThread.join()
    nusataraThread.join()
    mncThread.join()
    tvoneThread.join()
    tvriThread.join()
    deleteThread.join()

   

