from datetime import datetime, timedelta
from modules.mongo import GetOCRResult, deleteTimestamp
from utils.delete import tryDeleteFile


def deleteExpiredFile():
    threeDaysAgo= datetime.now() - timedelta(days=3)
    page = 1
    data, total, totalPage = GetOCRResult(date_to=threeDaysAgo, page=page)
    while total > 0:
        print(total)
        deleteData(data)
        data, total, totalPage = GetOCRResult(date_to=threeDaysAgo, page=1)

def deleteData(data):
    print("DELETE :", data)
    for d in data:
        succ = tryDeleteFile(d["result"])
        deleteTimestamp(d["_id"])


    
