import os
from datetime import datetime

def getTimestampFromFilename(name: str, channel = None) -> datetime | None:
    try:
        if channel == 'metrotv':
            x = name[-18:]
            x = x.replace('.mp4', '')
            x = x.split('-')
            # print(x)
            if len(x) != 5:
                print(x)
                print("PANIC: VIDEO FORMAT CHANGED. EXITTING")
                return None
            year = datetime.now().year
            this_month = datetime.now().month
            month = int(x[0])

            if (this_month == 1 and month == 12):
                return None
            second = int(x[4])
            day = int(x[1])
            hour = int(x[2])
            minutes = int(x[3])
            second = 0
        else:
            x = name[-18:]
            x = x.replace('.mp4', '')
            x = x.split('-')
            year = datetime.now().year
            this_month = datetime.now().month
            month = int(x[0])

            if (this_month == 1 and month == 12):
                return None
            day = int (x[1])
            hour = int(x[2])
            minutes = int (x[3])
            second = int(x[4])

        return datetime(year=year, month=month, day=day, hour=hour, minute=minutes, second=second) 
    except:
        return None



def getNextUnprocessVideo(path: str, lastProcessedTime: datetime, channel = None) -> tuple[str | None, datetime | None]:
    files = os.listdir(path)
    print(path)
    mp4 = [f for f in files if f.endswith('.mp4')]
    mp4 = [f for f in files if f.count('.mp4') == 1]
    mp4 = [f for f in files if 'converted' not in f]
    print(mp4)
    timestamps = [ getTimestampFromFilename(v, channel) for v in mp4]
    mp4WithTimestamps = zip(mp4, timestamps)
    print(mp4,timestamps, lastProcessedTime)
    mp4WithTimestamps = [ (a,b) for  (a,b) in mp4WithTimestamps if b is not None]
    sorted_by_timestamps = sorted(mp4WithTimestamps, key= lambda x: x[1])
    sorted_by_timestamps = [ x for x in sorted_by_timestamps if x[1] > lastProcessedTime]
    if len(sorted_by_timestamps) == 0:
        return None, None

    return sorted_by_timestamps[0][0], sorted_by_timestamps[0][1]




if __name__ == "__main__":
    print(getNextUnprocessVideo('/home/comvis/siputri/CNNSTREAMING', datetime(year=2024, month=10, day=7, hour=14)))
