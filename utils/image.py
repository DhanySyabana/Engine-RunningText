import cv2
sr = cv2.dnn_superres.DnnSuperResImpl_create()
  
path = "utils/ESPCN_x3.pb"
  
sr.readModel(path)
  
sr.setModel("espcn",3)

def preprocess(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    return equalized
def superRes(img):  
  result = sr.upsample(img)
  return result
