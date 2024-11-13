import os

def tryDeleteFile(path : str) -> bool:
    if not path.endswith('.mp4'):
        return False
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
        return True
    except Exception as e:
        print(e)
        return False



