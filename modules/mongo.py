import pymongo
import math
from datetime import datetime
client = pymongo.MongoClient("localhost", 27018)
db = client.comvis


def addTimestamp(source, result, dt: datetime, text, confidence=None):
    return db.results_test.insert_one({
        "source":source,
        "result": result,
        "time" : dt,
        "text" : text,
        "confidence": confidence
        })

def addNewWatchLog(dt: datetime, channel, startTime: datetime, tries = 0):
    return db.watch_log.insert_one({
            "time"  : dt,
            "channel": channel,
            "status" : "STARTED",
            "starttime": startTime,
            "tries": tries
        }).inserted_id

def updateWatchLogStatus(id, status, error = None, tries = None):
    update = {'status': status}
    if status =='COMPLETED' or status == 'FAILED':
        update["endtime"] = datetime.now()
    if error is not None:
        update["error"] = error
    update['tries'] = tries if tries is not None else 0
    print('update : ', update)
    return db.watch_log.update_one(
            {
                '_id' : id    
            }, 
            {
                '$set': update
            }
            )
def getLastProcessedVideo(channel):
    return db.watch_log.find_one({'channel': channel}, sort=[('starttime', -1)])
def deleteTimestamp(id):
    return db.result_ocr.delete_one({"_id":id})

def GetOCRResult(text : str | None = None, channels : list[str] | None = None, source : str | None = None, date_from : datetime | None = None, date_to : datetime | None = None, is_validated : bool = False, is_calculated: bool | None = None, page : int = 1, page_size : int = 10) -> tuple[list, int, int]:
        query = {}
        if text is not None:
            query['text'] = {"$regex": text, "$options": "i"}
        if channels is not None and len(channels) > 0:
            query['channel'] = {"$in" : channels}
        if source is not None:
            query['source'] = source
        if date_from is not None:
            if 'time' not in query:
                query['time'] = {}
            query['time']['$gte'] = date_from
        if date_to is not None:
            if 'time' not in query:
                query['time'] = {}
            query['time']["$lte"] = date_to
        if is_validated:
            query['is_validated'] = is_validated

        if is_calculated is not None:
            query['ad_value'] = {"$exists": is_calculated}

        # query['is_deleted'] = {"$ne": True}

        if page > 0 and page_size > 0:
            result = db.result_ocr.find(query).skip((page-1)*page_size).limit(page_size)
        else:
            result = db.result_ocr.find(query)


        print("GetOCRResult Query: ", query)

        result = result.sort({ 'time': -1 })
        result = list(result)

        total = db.result_ocr.count_documents(query)
        total_page = math.ceil(total/page_size)
        return result, total, total_page

def SaveResults(result, channel, channelAlias):                                                                                                               
    # print("Saving {} tweets to database...".format(len(tweets)))                                                                                        
    if len(result) == 0:                                                                                                                                  
        return None                                                                                                                                       
    bulk_update = []                                                                                                                                      
    for res in result:                                                                                                                                  
        bulk_update.append(pymongo.UpdateOne(
            {
                'result' : res['result'],
                'channel': channel,
                'channelAlias': channelAlias,
                'time': res['time']
            },
            {
                '$set' : {
                    **res,
                    'channel': channel
                },
            }, True
            ))                                                                                                                                                
    res = db['result_ocr'].bulk_write(bulk_update)                                                                                                                                                                                                                                      
    return res

if __name__ == '__main__':
    print(getLastProcessedVideo('metrfotv')['time'])
    
