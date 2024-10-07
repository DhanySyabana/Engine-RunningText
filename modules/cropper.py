import easyocr
import cv2
import numpy as np
import ffmpegcv
from moviepy import editor
from tqdm import tqdm
from typing import Literal
from jiwer import wer, cer
from modules.mongo import addTimestamp, deleteTimestamp
from functools import reduce

from utils.image import preprocess, superRes
from utils.text import overlap
from utils.wer import getCER, getWER
from paddleocr import PaddleOCR


VideoType = Literal['flip', 'run']

THRESHOLD_DIFF = 1000000
THRESHOLD_FRAME_WITHOUT_TEXT = 5 * 30
reader = easyocr.Reader(['id'], gpu=False, verbose=False)
#paddleReader = PaddleOCR(use_angle_cls=False, lang='id', det=False)

def formatMinute(sec):
    minutes = int(sec // 60)
    sec = sec % 60
    return f"{minutes}:{sec:0>2}"


def cropAndOcr(filename: str, type: VideoType, top: int, left: int, bottom: int, right: int, threshold, folderOutput: str = 'output'):
    if type == 'flip':
        CropThenOcrFlip(filename, top, left, bottom, right, threshold, folderOutput)
    elif type == 'run':
        OcrThenCropRunning(filename, top, left, bottom, right, threshold, folderOutput)

def CropThenOcrFlip(videoFilename, top: int, left: int, bottom: int, right: int, threshold,  folderOutput: str = 'output'):
    video = cv2.VideoCapture(videoFilename)
    fps = video.get(cv2.CAP_PROP_FPS)
    croppedBefore = None
    videoHeight = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    videoWidth = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    fpsProccess = round(fps * 0.5)
    fpsElapsed = 0
    timestampToCut = []
    diffStart = None
    lastAdded = False
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

    before = 0
    filteredTimestamp = []
    for timestamp in timestampToCut:
        if timestamp - before > 0.5 * fps:
            filteredTimestamp.append((before, timestamp - fpsProccess))
        before = timestamp
    #print(fps)
    #print(filteredTimestamp)

    ocrFilteredTimestamp = []
    wordBefore = None
    idBefore = None
    for timestamp in tqdm(filteredTimestamp):
        startframe = int(timestamp[0])
        endframe = int(timestamp[1])
        video.set(cv2.CAP_PROP_POS_FRAMES, startframe)
        textBefore = None
        fpsElapsed = startframe

        while video.get(cv2.CAP_PROP_POS_FRAMES) < endframe:
            ret, frame = video.read()
            if fpsElapsed % fpsProccess != 0:
                fpsElapsed += 1
                continue
            fpsElapsed += 1

            cropped = frame[top:bottom, left:right]
            
            read = reader.readtext(cropped)
            if len(read) == 0:
                continue
            if len(read) >= 1:
                read = [(None, ' '.join([x[1] for x in read]), reduce(lambda x, y: x + y, [x[2] for x in read]) / len(read))]

            if textBefore is not None:

                if textBefore[2] < read[0][2]:
                    textBefore = read[0]
            else:
                textBefore = read[0]
        if textBefore is not None:
            if wordBefore is not None:
                if getCER(textBefore[1], wordBefore[1]  ) < 0.7:
                    # if wordnya sama dengan sebelumnya, merge dan ambil yang confidence paling tinggi
                    if textBefore[2] < wordBefore[2]:
                        textBefore = wordBefore

                    timeStampBefore = ocrFilteredTimestamp.pop()
                    deleteTimestamp(idBefore)
                    ocrFilteredTimestamp.append((timeStampBefore[0], endframe, textBefore))
                    ret = addTimestamp(videoFilename, formatMinute(timeStampBefore[0] / fps), formatMinute(endframe / fps), textBefore[1], textBefore[2])

                    wordBefore = textBefore
                    idBefore = ret.inserted_id
                    continue
                
            if textBefore[2] > 0.0:
                ocrFilteredTimestamp.append((startframe, endframe, textBefore))
                ret = addTimestamp(videoFilename, formatMinute(startframe / fps), formatMinute(endframe / fps), textBefore[1], textBefore[2])
                idBefore = ret.inserted_id

            else:
                # ! for now, recognition with small confidence will be saved
                ret = addTimestamp(videoFilename, formatMinute(startframe / fps), formatMinute(endframe / fps), textBefore[1], textBefore[2])
                ocrFilteredTimestamp.append((startframe, endframe, textBefore))
                idBefore = ret.inserted_id

        wordBefore = textBefore
        

    video = editor.VideoFileClip(videoFilename)
    i = 0
    for timestamp in tqdm(ocrFilteredTimestamp):
        #video.crop(x1=left, x2=right, y1=top, y2=bottom).subclip(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/{folderOutput}/outputCropped_{i}.mp4'
        #, codec='mpeg4', fps=video.fps, logger=None)
        video.subclip(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/{folderOutput}/{videoFilename.split("/")[1].split(".")[0].replace(" ", "_")}_outputOriginal_{i}.mp4'
        , codec='mpeg4', fps=video.fps, logger=None)   
        i += 1

def OcrThenCropRunning(videoFilename, top: int, left: int, bottom: int, right: int, threshold,  folderOutput: str = 'output'):
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
    while (cap.isOpened()):
        ret, frame = cap.read()
        if not ret:
            if concatenatedText != "":
                timestampToCut.append((textStart, (fpsElapsed - fpsProccess)))
                addTimestamp(videoFilename, formatMinute(textStart / fps), formatMinute((fpsElapsed - fpsProccess) / fps), concatenatedText, None)
            break
        if (fpsElapsed % fpsProccess != 0):
          fpsElapsed += 1
          continue
        fpsElapsed += 1
        
        cropped = frame[top:bottom, left:right]
        texts = reader.readtext(cropped)

        if (texts):
          #print(formatMinute(fpsElapsed / fps))
          #print(texts)
          textWORight = []
          if len(texts) > 1:
              before = None
              for text in texts:
                  coord = text[0]
                  topRight = coord[1]
                  mostRight = topRight[0]
                  topLeft = coord[0]
                  mostLeft = topLeft[0]
                  if before is None:
                      before = mostRight
                      textWORight.append(text)
                      continue
                  delta = mostLeft - before
                  if delta < 10:
                      textWORight.append(text)
                      before = mostRight
                  else:
                      break 
          else:
              textWORight = texts
          #print(textWORight)
          #print(texts)

          leftText = ' '.join([x[1] for x in textWORight])
          if len(texts) < 2:
            rightText = leftText
          else:
            if len(texts) == len(textWORight):
                rightText = texts[-1][1]
            else:
                rightText = texts[len(textWORight)][1]
          if (wordbefore is not None):
            #print("before", wordbefore)
            #print("left", leftText)
            werR = getCER(wordbefore, leftText)
            werL = getCER(leftText, wordbefore)
            #print("R", werR)
            #print("L", werL)
            wer = werR + werL
            if wer > 3:
              if concatenatedText != "":
                  timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText + 1))))
                  addTimestamp(videoFilename, formatMinute(textStart / fps), formatMinute((fpsElapsed - fpsProccess*(frameNoText + 1))  / fps), concatenatedText, None)
   
              wordbefore = leftText
              concatenatedText = leftText
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
                timestampToCut.append((textStart, (fpsElapsed - fpsProccess*(frameNoText + 1))))
                addTimestamp(videoFilename, formatMinute(textStart / fps), formatMinute((fpsElapsed - fpsProccess*(frameNoText + 1))  / fps), concatenatedText, None)

                concatenatedText = ""
                wordbefore = None
            frameNoText = 0

        
    video = editor.VideoFileClip(videoFilename)
    i = 0
    for timestamp in tqdm(timestampToCut):
        #video.crop(x1=left, x2=right, y1=top, y2=bottom).subclip(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/{folderOutput}/outputCropped_{i}.mp4'
        #, codec='mpeg4', fps=video.fps, logger=None)
        video.subclip(timestamp[0] / fps, timestamp[1] / fps).write_videofile(f'videos/{folderOutput}/{videoFilename.split("/")[1].split(".")[0].replace(" ", "_")}_outputOriginal_{i}.mp4'
        , codec='mpeg4', fps=video.fps, logger=None)   
        i += 1


        

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


