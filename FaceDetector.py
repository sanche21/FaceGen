import cv2
from DataLoader import LoadFilesData, DataLoader
import numpy as np
from Visualization import visualizeImages
import glob
from math import ceil
from NeuralNet import NeuralNet
from Sampler import randomSample

def detectedFace(image, cascadePath="./cascades"):
    for thisCascade in glob.glob(cascadePath+"/*.xml"):
        #convert to grayscale
        grayImage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        #perform opencv face detection
        faceCascade = cv2.CascadeClassifier(thisCascade)
        faces = faceCascade.detectMultiScale(
            grayImage,
            scaleFactor=1.1,
            minNeighbors=0,
            minSize=(32, 32),
            maxSize=(64, 64),
        )
        if len(faces) > 0:
            return True
    return False

def detectErrorRate(imageMat):
    # convert to 8 bit int
    imageSet = ((imageMat + 1) * (255 / 2)).astype(np.uint8)
    numImages = imageSet.shape[0]
    numFound = 0
    errMat = np.zeros_like(imageSet)
    for i in range(numImages):
        thisImage = imageSet[i, :, :, :]
        foundFace = detectedFace(thisImage)
        if not foundFace:
            errMat[numFound, :, ::] = thisImage
            numFound = numFound + 1
    print ("Error Rate: "  + str(float(numFound*100)/numImages) + "% (" + str(numFound) + "/" + str(numImages) +")")
    return errMat[:numFound, :, :, :]


def errorInDataset(imageCount):
    datasetDir = "/home/sanche/Datasets/IMDB-WIKI"
    csvPath = "./dataset.csv"
    indicesPath = "./indices.p"
    csvdata, indices = LoadFilesData(datasetDir, csvPath, indicesPath)
    numPerBin = int(ceil(imageCount/16.0))
    loader = DataLoader(indices, csvdata, numPerBin=numPerBin, imageSize=64, numWorkerThreads=10, bufferMax=20,
                        debugLogs=False, useCached=False)
    loader.start()
    batchDict = loader.getData()
    imageSet = batchDict["image"]
    #shuffle, so if some are trimmed, we are randomly from all bins
    np.random.shuffle(imageSet)
    detectErrorRate(imageSet[:imageCount,:,:,:])

def errorInGenerated(imageCount):
    # initialize the data loader
    image_size = 64
    batch_size = 64
    noise_size = 100

    # start training
    network = NeuralNet(batch_size=batch_size, image_size=image_size, noise_size=noise_size, learningRate=5e-4)

    sample = randomSample(network, imageCount)
    detectErrorRate(sample)

if __name__ == "__main__":
    sampleSize = 10000

    errorInDataset(sampleSize)
    errorInGenerated(sampleSize)



