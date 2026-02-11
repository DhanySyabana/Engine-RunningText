

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

        print(channelPath, lastTime, channel)
        filePath, timestamps = getNextUnprocessVideo(channelPath, lastTime, channel )
        print(filePath,timestamps)
        # timestamps = datetime.today()

        if filePath is None or timestamps is None:
            return
        #shutil.copy(channelPath+ '/' + filePath, 'temp/' )
        # id = addNewWatchLog(timestamps, channel, datetime.now())
        # res = cropAndOcr(file, timestamps, **properties.tv[channel], logId=id, folderOutput=f'{channel}' )
        print(filePath)
        res = cropAndOcr(channelPath+ '/' + filePath, timestamps, **properties.tv[channel], logId=id, folderOutput=f'{channel}' )
        print(res)

        # sr = SaveResults(res, channel, properties.tv[channel]['alias'])

        # print(sr)
        torch.cuda.empty_cache()
       
        # updateWatchLogStatus(id, 'COMPLETED')
        i+=1
    except Exception as e:
        print("CATCHED: ", e)
        print(traceback.format_exc())
        # if id is not None:
        #     updateWatchLogStatus(id, 'FAILED', repr(e) )
        return

def deleteRoutine():
    try:
        deleteExpiredFile()
    except Exception as e:
        print(e)
        print(traceback.format_exc)
        return

if __name__ == '__main__':
    # metroThread = threading.Thread(target=run, args=('metrotv', '/home/comvis/siputri/METROTVSTREAMING'))
    #kompasThread = threading.Thread(target=run, args=('kompastv', '/home/comvis/siputri/KOMPASSTREAMING'))
    # cnnThread = threading.Thread(target=run, args=('cnn', '/home/comvis/siputri/CNNSTREAMING'))
    # trans7Thread = threading.Thread(target=run, args=('trans7', '/home/comvis/remote1/TRANS7STREAMING'))
    # berita1Thread = threading.Thread(target=run, args=('beritasatu', '/home/comvis/siputri/BERITASATUSTREAMING'))
    # garudaThread = threading.Thread(target=run, args=('garuda','/home/comvis/remote1/GARUDASTREAMING'))

    # idxThread = threading.Thread(target=run, args=('idxchannel', '/home/comvis/siputri/IDXSTREAMING'))
    # inewsThread = threading.Thread(target=run, args=('inewstv', '/home/comvis/remote1/INEWSSTREAMING'))
    # nusataraThread = threading.Thread(target=run, args=('nusantaratv', '/home/comvis/remote1/NUSANTARATVSTREAMING'))
    # mncThread = threading.Thread(target=run, args=('mnctv', '/home/comvis/remote2/MNCSTREAMING'))
    # tvoneThread = threading.Thread(target=run, args=('tvone','/home/comvis/siputri/TVONESTREAMING'))
    tvriThread = threading.Thread(target=run, args=('tvri', '/home/comvis/remote1/TVRISTREAMING'))
    #deleteThread = threading.Thread(target=deleteRoutine)

    # metroThread.start()
    #kompasThread.start()
    # cnnThread.start()
    #trans7Thread.start() 
    # berita1Thread.start()
    # garudaThread.start()
    #idxThread.start()
    # inewsThread.start()
    # nusataraThread.start()
    # mncThread.start()
    # tvoneThread.start()
    tvriThread.start()
    #deleteThread.start()

    # metroThread.join()
    #kompasThread.join()
    # cnnThread.join()
    #trans7Thread.join() 
    # berita1Thread.join()
    # garudaThread.join()
    #idxThread.join()
    # inewsThread.join()
    # nusataraThread.join()
    # mncThread.join()
    # tvoneThread.join()
    tvriThread.join()
    #deleteThread.join()

   

