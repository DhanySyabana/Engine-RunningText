import pymongo
client = pymongo.MongoClient("localhost", 27018)
db = client.comvis


def addTimestamp(filename, timestart, timeend, text, confidence=None):
    return db.results_test.insert_one({
        "filename":filename,
        "timestart":timestart,
        "timeend": timeend,
        "text" : text,
        "confidence": confidence
        })
def deleteTimestamp(id):
    return db.results_test.delete_one({"_id":id})
    
