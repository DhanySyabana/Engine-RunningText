from datetime import datetime, timedelta
import easyocr
import cv2
import numpy as np
import subprocess
import os
from typing import Literal
from modules.mongo import updateWatchLogStatus
from functools import reduce
from dotenv import load_dotenv

from utils.text import overlap
from utils.wer import getCER

load_dotenv()
OUTPUT_FOLDER = os.path.expanduser(os.getenv("OUTPUT_FOLDER", r"D:\Medmon\storage\comvis"))

VideoType = Literal['flip', 'run']

THRESHOLD_DIFF = 1000000
THRESHOLD_FRAME_WITHOUT_TEXT = 5 * 30

# --- OPTIMIZATION: Lazy-loaded EasyOCR reader (singleton) ---
# Model is only loaded when first needed, not at module import time.
_reader = None
def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['id'], gpu=True, verbose=True)
    return _reader

# Minimum pixel difference to trigger OCR (change-detection gate).
# Below this, frames are considered identical and OCR is skipped.
# Tuned for small ticker crop regions (~400x16 pixels, 3 channels).
SKIP_OCR_DIFF_THRESHOLD = 15000


def formatOCRResult(source, result, dt: datetime, text, duration: float, confidence=None):
    normalized_text = text.upper() if isinstance(text, str) else text
    return {
        "source":source,
        "result": result,
        "time" : dt,
        "text" : normalized_text,
        "confidence": confidence,
        "duration": duration,
        "is_validated": False
        }

def formatMinute(sec):
    minutes = int(sec // 60)
    sec = sec % 60
    return f"{minutes}:{sec:0>2}"


def cut_video_ffmpeg(input_path, output_path, start_sec, end_sec, top, left, bottom, right):
    """Cut and crop video using ffmpeg with libx264 encoding.
    
    Since the crop region is very small (ticker area ~400x16px),
    re-encoding is negligible CPU compared to full-frame encoding.
    """
    crop_w = right - left
    crop_h = bottom - top

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cmd = [
        'ffmpeg', '-y',
        '-ss', f'{start_sec:.3f}',
        '-to', f'{end_sec:.3f}',
        '-i', input_path,
        '-vf', f'crop={crop_w}:{crop_h}:{left}:{top}',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-an',
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr.decode('utf-8', errors='ignore')[-500:]}")
    except Exception as e:
        print(f"ffmpeg exception: {e}")


def cropAndOcr(filename: str, dt: datetime, type: VideoType, top: int, left: int, bottom: int, right: int, threshold, alias, logId, folderOutput: str = 'output') -> list:
    if type == 'flip':
        return CropThenOcrFlip(filename, dt, top, left, bottom, right, threshold, logId, folderOutput)
    elif type == 'run':
        return OcrThenCropRunning(filename, dt, top, left, bottom, right, threshold, logId, folderOutput)

def CropThenOcrFlip(videoFilename, dt: datetime, top: int, left: int, bottom: int, right: int, threshold, logId,  folderOutput: str = 'output') -> list:
    video = cv2.VideoCapture(videoFilename)
    fps = (video.get(cv2.CAP_PROP_FPS))
    croppedBefore = None
    videoHeight = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    videoWidth = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))

    # OPTIMIZATION: Increase sampling interval from 0.5s to 1.0s for change detection
    fpsProccess = round(fps * (1.0))
    fpsElapsed = 0
    timestampToCut = []
    diffStart = None
    lastAdded = False

    updateWatchLogStatus(logId, 'RUNNING')

    # === PASS 1: Change detection with grab() optimization ===
    while video.isOpened():
        # OPTIMIZATION: Use grab() for frames we skip (no CPU-heavy decoding)
        if fpsElapsed % fpsProccess != 0:
            grabbed = video.grab()
            if not grabbed:
                lastAdded = True
                timestampToCut.append(fpsElapsed)
                break
            fpsElapsed += 1
            continue

        ret, frame = video.read()

        if not ret:
            lastAdded = True
            timestampToCut.append(fpsElapsed)
            break

        fpsElapsed += 1

        cropped = frame[top:bottom, left:right]

        if (croppedBefore is not None):
            diff = cv2.absdiff(croppedBefore, cropped)
            sumDiff = np.sum(diff)
            if (sumDiff > threshold):
                croppedBefore = None
                timestampToCut.append(fpsElapsed)
        croppedBefore = cropped

    if not lastAdded:
        timestampToCut.append(fpsElapsed)

    before = 0
    filteredTimestamp = []
    for timestamp in timestampToCut:
        filteredTimestamp.append((before, timestamp))
        before = timestamp

    # === PASS 2: OCR — optimized key-frame approach ===
    # Instead of OCR-ing every sampled frame in a segment,
    # only OCR 1-3 key frames (start-region, middle, end-region).
    reader = get_reader()
    ocrFilteredTimestamp = []
    wordBefore = None
    ocrResult = []
    i = 1
    for timestamp in filteredTimestamp:
        startframe = timestamp[0]
        endframe = timestamp[1]
        segment_length = endframe - startframe

        # Skip very short segments (< 0.5 seconds) — likely noise
        if segment_length < fps * 0.5:
            continue

        # OPTIMIZATION: Select 1-3 key frames instead of every sampled frame
        if segment_length <= fpsProccess * 2:
            # Short segment: just OCR the middle frame
            key_frames = [startframe + segment_length // 2]
        else:
            # Longer segment: OCR 3 evenly-spaced frames
            margin = min(fpsProccess, segment_length // 6)
            key_frames = [
                startframe + margin,
                startframe + segment_length // 2,
                endframe - margin
            ]

        textBefore = None
        for kf in key_frames:
            video.set(cv2.CAP_PROP_POS_FRAMES, kf)
            ret, frame = video.read()
            if not ret:
                continue

            cropped = frame[top:bottom, left:right]
            read = reader.readtext(cropped)
            if len(read) == 0:
                continue
            if len(read) >= 1:
                read = [(None, ' '.join([x[1] for x in read]), reduce(lambda x, y: x + y, [x[2] for x in read]) / len(read))]

            if textBefore is not None:
                if getCER(textBefore[1], read[0][1]) < 0.7:
                    if textBefore[2] < read[0][2]:
                        textBefore = read[0]
                else:
                    break
            textBefore = read[0]

        if textBefore is not None:
            if wordBefore is not None:
                if getCER(textBefore[1], wordBefore[1]  ) < 0.5:

                    # if wordnya sama dengan sebelumnya, merge dan ambil yang confidence paling tinggi
                    if textBefore[2] < wordBefore[2]:
                        textBefore = wordBefore
                    timeStampBefore = ocrFilteredTimestamp.pop()
                    timeStampBefore = (timeStampBefore[0], endframe, textBefore, timeStampBefore[3])
                    ocrFilteredTimestamp.append(timeStampBefore)
                    ocrBefore = ocrResult.pop()
                    ocrBefore['text'] = textBefore[1].upper() if isinstance(textBefore[1], str) else textBefore[1]
                    ocrBefore['confidence'] = textBefore[2]

                    duration = (endframe - timeStampBefore[0]) / fps
                    ocrBefore['duration'] = duration
                    ocrResult.append(ocrBefore)

                    wordBefore = textBefore
                    continue
                wordBefore = None
                
            if textBefore[2] > 0.0:
                timeStart = dt + timedelta(seconds=startframe/fps)
                timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
                path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
                print("RESULT FINAL: ", textBefore)
                ocrFilteredTimestamp.append((startframe, endframe, textBefore, path))

                duration = (endframe - startframe) / fps
                ret = formatOCRResult(videoFilename, path, timeStart, textBefore[1], duration, textBefore[2])
                ocrResult.append(ret)
                wordBefore = textBefore
            else:
                # ! for now, recognition with small confidence will be saved
                timeStart = dt + timedelta(seconds=startframe/fps)
                timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
                path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
                duration = (endframe - startframe) / fps

                ret = formatOCRResult(videoFilename, path, timeStart, textBefore[1], duration, textBefore[2])
                ocrResult.append(ret)

        i+=1
    print(len(ocrFilteredTimestamp), len(filteredTimestamp))
    video.release()

    # === PASS 3: Video cutting with ffmpeg (replaces moviepy) ===
    # Uses cropped output + ultrafast preset — negligible CPU for tiny ticker regions
    for timestamp in (ocrFilteredTimestamp):
        start_sec = timestamp[0] / fps
        end_sec = timestamp[1] / fps
        cut_video_ffmpeg(videoFilename, timestamp[3], start_sec, end_sec, top, left, bottom, right)

    return ocrResult

# def OcrThenCropRunning(videoFilename, dt: datetime, top: int, left: int, bottom: int, right: int, threshold, logId,  folderOutput: str = 'output') -> list:
#     timestampToCut = []
#     cap = cv2.VideoCapture(videoFilename)
#     frameBefore = None

#     fps = round(cap.get(cv2.CAP_PROP_FPS))
#     # OPTIMIZATION: Increase sampling interval from 0.5s to 1.0s
#     fpsProccess = round(fps * (1.0))
#     fpsElapsed = 0
#     wordbefore = None
#     concatenatedText = ""
#     textStart = 0
#     frameNoTextThreshold = 10
#     frameNoText = 0
#     frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) 
#     print(frames)
#     print(fps)
#     print(cap.get(cv2.CAP_PROP_FPS))

#     updateWatchLogStatus(logId, 'RUNNING')
#     reader = get_reader()
#     ocrResult = []

#     # For change-detection gated OCR
#     croppedBefore = None

#     while (cap.isOpened()):
#         # OPTIMIZATION: Use grab() for frames we skip (no CPU-heavy decoding)
#         if (fpsElapsed % fpsProccess != 0):
#             grabbed = cap.grab()
#             if not grabbed:
#                 # End of video — same finalization as original
#                 if concatenatedText != "" and textStart < frames:
#                     fpsElapsed = min(frames, fpsElapsed)
#                     timestampToCut.append((textStart, (fpsElapsed)))
#                     timeStart = dt + timedelta(seconds=textStart / fps)
#                     timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
#                     path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
#                     duration = (fpsElapsed - textStart) / fps
#                     ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
#                     ocrResult.append(ret)
#                 break
#             fpsElapsed += 1
#             continue

#         ret, frame = cap.read()
#         if not ret:
#             if concatenatedText != "" and textStart < frames:
#                 fpsElapsed = min(frames, fpsElapsed)
#                 timestampToCut.append((textStart, (fpsElapsed)))
#                 timeStart = dt + timedelta(seconds=textStart / fps)
#                 timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
#                 path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
#                 duration = (fpsElapsed - textStart) / fps
#                 ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
#                 ocrResult.append(ret)
#             break
#         fpsElapsed += 1
        
#         cropped = frame[top:bottom, left:right]

#         # OPTIMIZATION: Change-detection gated OCR
#         # Skip OCR if the ticker area hasn't changed significantly.
#         # For running text: text scrolling causes large pixel diffs (above threshold),
#         # so OCR only skips when ticker is truly static (empty or frozen).
#         if croppedBefore is not None:
#             diff = cv2.absdiff(croppedBefore, cropped)
#             sumDiff = np.sum(diff)
#             if sumDiff < SKIP_OCR_DIFF_THRESHOLD:
#                 # Frame nearly identical — for running text, this means no scrolling.
#                 # Increment frameNoText so segment finalization can trigger.
#                 croppedBefore = cropped
#                 frameNoText += 1
#                 if frameNoText > frameNoTextThreshold:
#                     if concatenatedText != "":
#                         timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText - 1))))
#                         timeStart = dt + timedelta(seconds=textStart/fps)
#                         timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
#                         path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
#                         duration = ((fpsElapsed - fpsProccess*(frameNoText - 1)) - textStart) / fps
#                         ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
#                         ocrResult.append(ret)
#                     textStart = fpsElapsed
#                     concatenatedText = ""
#                     wordbefore = None
#                     frameNoText = 0
#                 continue
#         croppedBefore = cropped.copy()

#         # --- Original OCR logic (preserved for accuracy) ---
#         texts = reader.readtext(cropped)

#         if (texts):
#           textWORight = []

#           limiter = [' 0', '~0', '-0', '\'0', '\"0', '+0', 'K0', 'P0', ' @', '~@', '-@', '\'@', '\"@', '+@', 'K@', 'K0',' O', '~O', '-O', '\'O', '+O', '\"O']
#           oneCharLimiter =['0', '@']
#           specialLimier = [' \'', ' \"']
#           if len(texts) > 1:
#               before = None
#               bb = None
#               for text in texts:
#                   coord = text[0]
#                   topRight = coord[1]
#                   mostRight = topRight[0]
#                   topLeft = coord[0]
#                   mostLeft = topLeft[0]
#                   if before is None:
#                       before = mostRight
#                       bb=text[1]
#                       textWORight.append(text)
#                       continue
#                   delta = mostLeft - before

#                   stripped = ''
#                   if bb is not None:
#                       stripped = bb.strip()
#                   if folderOutput == 'tvri':
#                       thresss = 3 if wordbefore is not None and ((stripped[-2::] in limiter) or (stripped[-2::] in specialLimier) or (stripped[-1::] in oneCharLimiter)) else 11
#                   else:
#                       thresss = 11

#                   if delta < thresss:
#                       textWORight.append(text)
#                       before = mostRight
#                       bb = text[1]
#                   else:
#                       break 
#           else:
#               textWORight = texts

          
#           leftText = ' '.join([x[1] for x in textWORight])
#           if folderOutput == 'tvri':
#               for l in limiter:
#                   leftText = leftText.replace(l +' ', '++++++++++++++')
#               leftText = leftText.split('++++++++++++++')[0]
#           if len(texts) < 2:
#             rightText = leftText
#           else:
#             if len(texts) == len(textWORight):
#                 rightText = texts[-1][1]
#             else:
#                 rightText = texts[len(textWORight)][1]
#           if (wordbefore is not None):
#             print("before: ", wordbefore)
#             print("left: ", leftText)
#             print(concatenatedText)
#             print(texts)
#             werR = getCER(wordbefore, leftText)
#             werL = getCER(leftText, wordbefore)
#             print("R: ", werR)
#             print("L: ", werL)

#             print('\n\n')
#             wer = werR + werL
#             if wer > 3:
#               if concatenatedText != "":
#                   print("FINAL: ", concatenatedText, "=========================================================================")
#                   timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText - 1))))
#                   timeStart = dt + timedelta(seconds=textStart/fps)
#                   timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
#                   path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
#                   duration = ((fpsElapsed - fpsProccess*(frameNoText - 1)) - textStart) / fps
#                   ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
#                   ocrResult.append(ret)


   
#               wordbefore = None
#               concatenatedText = ""
#               textStart = fpsElapsed
#             else:
#               wordbefore = leftText 
#               concatenatedText = overlap(concatenatedText, leftText)
#           else:
#             wordbefore = leftText 

#             concatenatedText = leftText
#             textStart = fpsElapsed

#           frameNoText = 0
#         else:
#           frameNoText += 1
#           if frameNoText > frameNoTextThreshold:
#             if concatenatedText != "":
#                 timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText - 1))))
#                 timeStart = dt + timedelta(seconds=textStart/fps)
#                 timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
#                 path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
#                 duration = ((fpsElapsed - fpsProccess*(frameNoText - 1)) - textStart) / fps
#                 ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
#                 ocrResult.append(ret)

            
#             textStart = fpsElapsed
#             #reset nonetheless
#             concatenatedText = ""
#             wordbefore = None
#             frameNoText = 0

#     cap.release()  

#     # === Video cutting with ffmpeg (replaces moviepy) ===
#     for timestamp in timestampToCut:
#         time = dt + timedelta(seconds=timestamp[0]/ fps) 
#         timestr = time.strftime("%Y_%m_%d_%H_%M_%S")
#         path = f'D:\\Medmon\\storage\\comvis\\{folderOutput}_{timestr}.mp4'
#         start_sec = timestamp[0] / fps
#         end_sec = timestamp[1] / fps

#         try:
#             cut_video_ffmpeg(videoFilename, path, start_sec, end_sec, top, left, bottom, right)
#         except Exception as e:
#             print(e)
#             print(timestamp)
#             print(start_sec, end_sec)

#     return ocrResult
