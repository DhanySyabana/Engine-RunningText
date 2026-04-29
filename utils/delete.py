import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def tryDeleteFile(path : str) -> bool:
    if not path.endswith('.mp4'):
        return False
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
        return True
    except Exception as e:
        logger.error(f"Error deleting file {path}: {e}")
        return False



