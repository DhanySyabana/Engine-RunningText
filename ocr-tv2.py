

import sys
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
import torch

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
    id = None

    tries = 0
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
                if last['status'] != "FAILED":
                    s = updateWatchLogStatus(last["_id"], "FAILED")
                s = last
                tries = last['tries'] if last['tries'] is not None else 0
                print('Last s: ', last)
                print('S: ', s)
                if tries <= 15:
                    lastTime = last["time"] - timedelta(minutes=2)
                else:
                    # skip and reset tries
                    lastTime = last["time"]
                    tries = 0
            else:
                # reset tries
                lastTime = last['time']
                tries = 0

        filePath, timestamps = getNextUnprocessVideo(channelPath, lastTime, channel )


        if filePath is None or timestamps is None:
            return
        #shutil.copy(channelPath+ '/' + filePath, 'temp/' )

        now = datetime.now()
        delta = now - timestamps
        
        #skipping if file is in writing
        print(delta.seconds / 60)
        if delta.total_seconds() / 60 < 20:
            return

        print(properties.tv[channel])
        id = addNewWatchLog(timestamps, channel, datetime.now(), tries)
        res = cropAndOcr(channelPath+ '/' + filePath, timestamps, **properties.tv[channel], logId=id, folderOutput=f'{channel}' )

        
        sr = SaveResults(res, channel, properties.tv[channel]['alias'])
        torch.cuda.empty_cache()
        print(sr)
       
        updateWatchLogStatus(id, 'COMPLETED')
        
        i+=1
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        if id is not None:
            updateWatchLogStatus(id, 'FAILED', repr(e), tries + 1 )
        return

def deleteRoutine():
    try:
        deleteExpiredFile()
    except Exception as e:
        print(e)
        print(traceback.format_exc)
        return

if __name__ == '__main__':
    #metroThread = threading.Thread(target=run, args=('metrotv', '/home/comvis/siputri/METROTVSTREAMING'))
    #kompasThread = threading.Thread(target=run, args=('kompastv', '/home/comvis/siputri/KOMPASSTREAMING'))
    #cnnThread = threading.Thread(target=run, args=('cnn', '/home/comvis/siputri/CNNSTREAMING'))
    ##trans7Thread = threading.Thread(target=run, args=('trans7', '/home/comvis/remote1/TRANS7STREAMING'))
    #berita1Thread = threading.Thread(target=run, args=('beritasatu', '/home/comvis/siputri/BERITASATUSTREAMING'))
    idxThread = threading.Thread(target=run, args=('idxchannel', '/home/comvis/siputri/IDXSTREAMING'))
    inewsThread = threading.Thread(target=run, args=('inewstv', '/home/comvis/remote1/INEWSSTREAMING'))
    # nusataraThread = threading.Thread(target=run, args=('nusantaratv', '/home/comvis/remote1/NUSANTARATVSTREAMING'))
    # mncThread = threading.Thread(target=run, args=('mnctv', '/home/comvis/remote1/MNCSTREAMING'))
    # tvoneThread = threading.Thread(target=run, args=('tvone','/home/comvis/siputri/TVONESTREAMING'))
    tvoneThread = threading.Thread(target=run, args=('tvone','/home/comvis/remote2/TVONETVSTB'))
    #tvriThread = threading.Thread(target=run, args=('tvri', '/home/comvis/siputri/TVRISTREAMING'))
    #garudaThread = threading.Thread(target=run, args=('garuda','/home/comvis/remote1/GARUDASTREAMING'))
    #deleteThread = threading.Thread(target=deleteRoutine)

    #metroThread.start()
    #kompasThread.start()
    #cnnThread.start()
    ##trans7Thread.start() 
    #berita1Thread.start()
    idxThread.start()
    inewsThread.start()
    # nusataraThread.start()
    # mncThread.start()
    tvoneThread.start()
    # tvriThread.start()
    #garudaThread.start()
    #deleteThread.start()

    #metroThread.join()
    #kompasThread.join()
    #cnnThread.join()
    ##trans7Thread.join() 
    #berita1Thread.join()
    idxThread.join()
    inewsThread.join()
    # nusataraThread.join()
    # mncThread.join()
    tvoneThread.join()
    # tvriThread.join()
    #garudaThread.join()
    #deleteThread.join()

   

