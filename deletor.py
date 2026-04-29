

import os
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

        filePath, timestamps = getNextUnprocessVideo(channelPath, lastTime, channel )


        if filePath is None or timestamps is None:
            return
        #shutil.copy(channelPath+ '/' + filePath, 'temp/' )

        print(properties.tv[channel])
        id = addNewWatchLog(timestamps, channel, datetime.now())
        res = cropAndOcr(channelPath+ '/' + filePath, timestamps, **properties.tv[channel], logId=id, folderOutput=f'{channel}' )

        
        sr = SaveResults(res, channel, properties.tv[channel]['alias'])
        torch.cuda.empty_cache()
        print(sr)
       
        updateWatchLogStatus(id, 'COMPLETED')
        
        i+=1
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        return

def deleteRoutine():
    try:
        deleteExpiredFile()
    except Exception as e:
        print(e)
        print(traceback.format_exc)
    return

if __name__ == '__main__':
    deleteRoutine()

   

