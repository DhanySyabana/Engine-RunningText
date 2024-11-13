from datetime import datetime, timedelta
from modules.mongo import GetOCRResult, deleteTimestamp
from utils.delete import tryDeleteFile


def deleteExpiredFile():
    threeDaysAgo= datetime.now() - timedelta(days=3)
    page = 1
    data, total, totalPage = GetOCRResult(date_to=threeDaysAgo, page=page)
    while total > 0:
        deleteData(data)
        data, total, totalPage = GetOCRResult(date_to=threeDaysAgo)




def deleteData(data):
    print("DELETE :", data)
    for d in data:
        print(d)
        succ = tryDeleteFile(d["result"])
        if succ:
            deleteTimestamp(d["_id"])


    
