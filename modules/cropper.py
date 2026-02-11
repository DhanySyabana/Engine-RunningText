from datetime import datetime, timedelta
import easyocr
import cv2
import numpy as np
import ffmpegcv
from moviepy import VideoFileClip
from tqdm import tqdm
from typing import Literal
from jiwer import wer, cer
from modules.mongo import addTimestamp, deleteTimestamp, updateWatchLogStatus
from functools import reduce

from utils.image import preprocess, superRes
from utils.text import overlap
from utils.wer import getCER, getWER
from paddleocr import PaddleOCR


VideoType = Literal['flip', 'run']

THRESHOLD_DIFF = 1000000
THRESHOLD_FRAME_WITHOUT_TEXT = 5 * 30
reader = easyocr.Reader(['id'], gpu=True, verbose=True)
#paddleReader = PaddleOCR(use_angle_cls=False, lang='id', det=False)

def formatOCRResult(source, result, dt: datetime, text, duration: float, confidence=None):
    return {
        "source":source,
        "result": result,
        "time" : dt,
        "text" : text,
        "confidence": confidence,
        "duration": duration,
        "is_validated": False
        }

def formatMinute(sec):
    minutes = int(sec // 60)
    sec = sec % 60
    return f"{minutes}:{sec:0>2}"


def cropAndOcr(filename: str, dt: datetime, type: VideoType, top: int, left: int, bottom: int, right: int, threshold, alias, logId, folderOutput: str = 'output') -> list:
    print(type)
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
    fpsProccess = round(fps * 1)
    fpsElapsed = 0
    timestampToCut = []
    diffStart = None
    lastAdded = False

    updateWatchLogStatus(logId, 'RUNNING')
    while video.isOpened():
        ret, frame = video.read()

        if not ret:
            lastAdded = True
            #print(fpsElapsed)
            timestampToCut.append(fpsElapsed)
            break

        if fpsElapsed % fpsProccess != 0:

            fpsElapsed += 1
            continue

        fpsElapsed += 1

        cropped = frame[top:bottom, left:right]

        if (croppedBefore is not None):
            diff = cv2.absdiff(croppedBefore, cropped)
            sumDiff = np.sum(diff)
            if (sumDiff > threshold):
                #stop and start new video
                croppedBefore = None
                timestampToCut.append(fpsElapsed)
        croppedBefore = cropped

    if not lastAdded:
        timestampToCut.append(fpsElapsed)

    print(timestampToCut)

    before = 0
    filteredTimestamp = []
    for timestamp in timestampToCut:
        # if timestamp - before > 0.5 * fps:
            # filteredTimestamp.append((before, timestamp - fpsProccess))
        filteredTimestamp.append((before, timestamp))
        before = timestamp
    #print(fps)
    print(filteredTimestamp)
    print('sadasda')

    ocrFilteredTimestamp = []
    wordBefore = None
    ocrResult = []
    i = 1
    for timestamp in filteredTimestamp:
        startframe = timestamp[0]
        endframe = timestamp[1]
        video.set(cv2.CAP_PROP_POS_FRAMES, startframe)
        textBefore = None
        fpsElapsed = startframe
        print(startframe, endframe)
        while video.get(cv2.CAP_PROP_POS_FRAMES) < endframe:
            ret, frame = video.read()
            if fpsElapsed % fpsProccess != 0:
                fpsElapsed += 1
                continue
            fpsElapsed += 1

            if not ret:
                break

            cropped = frame[top:bottom, left:right]
            
            read = reader.readtext(cropped)
            if len(read) == 0:
                continue
            if len(read) >= 1:
                read = [(None, ' '.join([x[1] for x in read]), reduce(lambda x, y: x + y, [x[2] for x in read]) / len(read))]

            print("READ: " , read)
            if textBefore is not None:
                if getCER(textBefore[1], read[0][1]) < 0.7:
                    if textBefore[2] < read[0][2]:
                        textBefore = read[0]
                else:
                    break
            textBefore = read[0]

        if textBefore is not None:
            print("TEXTBEFORE: ", textBefore)
            if wordBefore is not None:
                print("WORDBEFORE: ", wordBefore)
                print("CER: ", getCER(textBefore[1], wordBefore[1]))
                if getCER(textBefore[1], wordBefore[1]  ) < 0.5:

                    # if wordnya sama dengan sebelumnya, merge dan ambil yang confidence paling tinggi
                    if textBefore[2] < wordBefore[2]:
                        textBefore = wordBefore
                    timeStampBefore = ocrFilteredTimestamp.pop()
                    timeStampBefore = (timeStampBefore[0], endframe, textBefore, timeStampBefore[3])
                    ocrFilteredTimestamp.append(timeStampBefore)
                    ocrBefore = ocrResult.pop()
                    ocrBefore['text'] = textBefore[1]
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
                path = f'videos/output/{folderOutput}/{folderOutput}_{timestr}.mp4'
                print("FINAL: ", textBefore)
                print("path: ", path)

                ocrFilteredTimestamp.append((startframe, endframe, textBefore, path))

                duration = (endframe - startframe) / fps
                ret = formatOCRResult(videoFilename, path, timeStart, textBefore[1], duration, textBefore[2])
                ocrResult.append(ret)
                wordBefore = textBefore
            else:
                # ! for now, recognition with small confidence will be saved
                timeStart = dt + timedelta(seconds=startframe/fps)
                timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
                path = f'videos/output/{folderOutput}/{folderOutput}_{timestr}.mp4'
                duration = (endframe - startframe) / fps

                ret = formatOCRResult(videoFilename, path, timeStart, textBefore[1], duration, textBefore[2])
                ocrResult.append(ret)

        print('\n\n') 
        i+=1
    # print(ocrFilteredTimestamp) 
    print(len(ocrFilteredTimestamp), len(filteredTimestamp))
    video.release()

    video = VideoFileClip(videoFilename)
    i = 0
    print(fps, video.fps)
    for timestamp in (ocrFilteredTimestamp):
        #video.crop(x1=left, x2=right, y1=top, y2=bottom).subclip(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/{folderOutput}/outputCropped_{i}.mp4'
        #, codec='mpeg4', fps=video.fps, logger=None)
        time = dt + timedelta(seconds=timestamp[0]/ fps) 
        timestr = time.strftime("%Y_%m_%d_%H_%M_%S")
        video.subclipped(timestamp[0] / fps, timestamp[1] / fps).write_videofile(timestamp[3], codec='libx264', fps=fps, logger=None)   
        i += 1
    video.close()

    return ocrResult

def OcrThenCropRunning(videoFilename, dt: datetime, top: int, left: int, bottom: int, right: int, threshold, logId,  folderOutput: str = 'output') -> list:
    timestampToCut = []
    cap = cv2.VideoCapture(videoFilename)
    frameBefore = None

    fps = round(cap.get(cv2.CAP_PROP_FPS))
    fpsProccess = round(fps * (0.5))
    fpsElapsed = 0
    wordbefore = None
    concatenatedText = ""
    textStart = 0
    frameNoTextThreshold = 10
    frameNoText = 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) 
    print(frames)
    print(fps)
    print(cap.get(cv2.CAP_PROP_FPS))

    updateWatchLogStatus(logId, 'RUNNING')
    ocrResult = []
    while (cap.isOpened()):
        ret, frame = cap.read()
        if not ret:
            # print(fpsElapsed)
            if concatenatedText != "" and textStart < frames:
                fpsElapsed = min(frames, fpsElapsed)
                timestampToCut.append((textStart, (fpsElapsed)))
                timeStart = dt + timedelta(seconds=textStart / fps)
                timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
                path = f'videos/output/{folderOutput}/{folderOutput}_{timestr}.mp4'
                duration = (fpsElapsed - textStart) / fps
                ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
                ocrResult.append(ret)
            break
        if (fpsElapsed % fpsProccess != 0):
          fpsElapsed += 1
          continue
        fpsElapsed += 1
        
        cropped = frame[top:bottom, left:right]
        texts = reader.readtext(cropped)
        print("RAWS: ", texts)
        if (texts):
          #print(formatMinute(fpsElapsed / fps))
          #print(texts)
          textWORight = []

          limiter = [' 0', '~0', '-0', '\'0', '\"0', '+0', 'K0', 'P0', ' @', '~@', '-@', '\'@', '\"@', '+@', 'K@', 'K0',' O', '~O', '-O', '\'O', '+O', '\"O']
          oneCharLimiter =['0', '@']
          specialLimier = [' \'', ' \"']
          if len(texts) > 1:
              before = None
              bb = None
              for text in texts:
                  coord = text[0]
                  topRight = coord[1]
                  mostRight = topRight[0]
                  topLeft = coord[0]
                  mostLeft = topLeft[0]
                  if before is None:
                      before = mostRight
                      bb=text[1]
                      textWORight.append(text)
                      continue
                  delta = mostLeft - before

                  stripped = ''
                  if bb is not None:
                      stripped = bb.strip()
                  if folderOutput == 'tvri':
                      thresss = 3 if wordbefore is not None and ((stripped[-2::] in limiter) or (stripped[-2::] in specialLimier) or (stripped[-1::] in oneCharLimiter)) else 11
                  else:
                      thresss = 11

                  if delta < thresss:
                      textWORight.append(text)
                      before = mostRight
                      bb = text[1]
                  else:
                      break 
          else:
              textWORight = texts

          
          leftText = ' '.join([x[1] for x in textWORight])
          if folderOutput == 'tvri':
              for l in limiter:
                  leftText = leftText.replace(l +' ', '++++++++++++++')
              leftText = leftText.split('++++++++++++++')[0]
          if len(texts) < 2:
            rightText = leftText
          else:
            if len(texts) == len(textWORight):
                rightText = texts[-1][1]
            else:
                rightText = texts[len(textWORight)][1]
          if (wordbefore is not None):
            print("before: ", wordbefore)
            print("left: ", leftText)
            print(concatenatedText)
            print(texts)
            werR = getCER(wordbefore, leftText)
            werL = getCER(leftText, wordbefore)
            print("R: ", werR)
            print("L: ", werL)

            print('\n\n')
            wer = werR + werL
            if wer > 3:
              if concatenatedText != "":
                  print("FINAL: ", concatenatedText, "=========================================================================")
                  timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText - 1))))
                  timeStart = dt + timedelta(seconds=textStart/fps)
                  timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
                  path = f'videos/output/{folderOutput}/{folderOutput}_{timestr}.mp4'
                  duration = ((fpsElapsed - fpsProccess*(frameNoText - 1)) - textStart) / fps
                  ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
                  ocrResult.append(ret)


   
              wordbefore = None
              concatenatedText = ""
              textStart = fpsElapsed
            else:
              wordbefore = leftText 
              concatenatedText = overlap(concatenatedText, leftText)
          else:
            wordbefore = leftText 

            concatenatedText = leftText
            textStart = fpsElapsed

          frameNoText = 0
          #print("concat", concatenatedText)
          #print()
        else:
          frameNoText += 1
          if frameNoText > frameNoTextThreshold:
            if concatenatedText != "":
                timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText - 1))))
                timeStart = dt + timedelta(seconds=textStart/fps)
                timestr= timeStart.strftime("%Y_%m_%d_%H_%M_%S")
                path = f'videos/output/{folderOutput}/{folderOutput}_{timestr}.mp4'
                duration = ((fpsElapsed - fpsProccess*(frameNoText - 1)) - textStart) / fps
                ret = formatOCRResult(videoFilename, path, timeStart, concatenatedText, duration, None)
                ocrResult.append(ret)

            
            textStart = fpsElapsed
            #rest nonetheless
            concatenatedText = ""
            wordbefore = None
            frameNoText = 0

    cap.release()  
    video = VideoFileClip(videoFilename)
    i = 0
    for timestamp in timestampToCut:
        #video.crop(x1=left, x2=right, y1=top, y2=bottom).subclip(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/{folderOutput}/outputCropped_{i}.mp4'
        #, codec='mpeg4', fps=video.fps, logger=None)
        time = dt + timedelta(seconds=timestamp[0]/ fps) 
        timestr = time.strftime("%Y_%m_%d_%H_%M_%S")

        # print(timestamp)
        try:
            video.subclipped(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/output/{folderOutput}/{folderOutput}_{timestr}.mp4'

        , codec='libx264', fps=video.fps, logger=None)   

        except Exception as e:
            print(e)
            print(timestamp)
            print(timestamp[0]/fps, timestamp[1]/fps)
        i += 1
    video.close()
    return ocrResult


        

#def formatPaddle(image):
#    result = paddleReader.ocr(image, cls=False)  
#    #print(result)
#    for i in range(len(result)):
#        #print(result[i])
#    if len(result) == 0 or result[0] is None:
#        return []
#    return [(x[0], x[1][0], x[1][1]) for x in result[0]]
#


def startWriting(filename: str, fps, width, height):
    writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    return writer


