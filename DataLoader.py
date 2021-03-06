import os
from scipy.io import loadmat
from scipy.misc import imread, imresize
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import pickle
import time
from PIL import Image
import threading
from copy import deepcopy
from random import  shuffle
""""
creates a csv file containing information on all the faces
uses the information from the dataset's .mat files, and applies filtering to keep only good quality data

Params
    datasetDir: the directory of the IMDBWIKI dataset on the computer's hard drive
    agetRange:  a vector containing the min and max age to keep. Helps trim out outlier errors in the dataset
    minScore:   the minimum face score to keep. Removes bad quality data
    minRes:     the minimum resolution image to keep
    filterGender:   a bool that determines whether to trim out faces with unlabeled geneders
    filterRGB:  determines whether we should filter out b/w images (or other encodings)
    filterMult: determines whether images with multiple faces should be filtered out

Returns
    0: the dataframe the .csv represents
"""
def createCsv(datasetDir, ageRange=[10, 100], minScore=1, minRes=(60*60), filterGender=True, filterRGB=True, filterMult=True):
    combinedDf = None
    for fileType in ["wiki", "imdb"]:
        matFile = loadmat(os.path.join(datasetDir, fileType+"_crop", fileType+".mat"))
        dateOfBirth = matFile[fileType]["dob"][0][0][0]
        yearTaken = matFile[fileType]["photo_taken"][0][0][0]
        path = matFile[fileType]["full_path"][0][0][0]
        gender = matFile[fileType]["gender"][0][0][0]
        name = matFile[fileType]["name"][0][0][0]
        faceLocation = matFile[fileType]["face_location"][0][0][0]
        faceScore = matFile[fileType]["face_score"][0][0][0]
        faceScore2 = matFile[fileType]["second_face_score"][0][0][0]

        numRows = dateOfBirth.shape[0]

        birthYear = np.zeros(numRows)
        age = np.zeros(numRows)
        imFormat = np.copy(name)
        imHeight = np.zeros(numRows, dtype=int)
        imWidth = np.zeros(numRows, dtype=int)
        imRes = np.zeros(numRows, dtype=int)

        for i in range(0, numRows):
            # add age/birth year
            matlabBD = dateOfBirth[i]
            if matlabBD < 366:
                matlabBD = 400
            pythonBd = datetime.fromordinal(int(matlabBD)) + timedelta(days=int(matlabBD) % 1) - timedelta(days=366)
            birthYear[i] = pythonBd.year
            age[i] = yearTaken[i] - pythonBd.year
            # fix name
            nameArr = name[i]
            if (nameArr.shape[0] > 0):
                name[i] = nameArr[0].replace(",", "")
            else:
                name[i] = ""
            # fix path
            pathArr = path[i]
            fullPath = os.path.join(datasetDir, fileType + "_crop", pathArr[0])
            path[i] = fullPath
            #add image data
            try:
                img = Image.open(fullPath)
                imFormat[i] = img.mode
                w, h = img.size
                imHeight[i] = w
                imWidth[i] = h
                imRes[i] = w * h
            except IOError:
                print("error reading file " + fullPath)
                imHeight[i] = -1
                imWidth[i] = -1
                imRes[i] = -1
            if i % 10000 == 0:
                print(str(i) + "/" + str(numRows))

        dataTable = {"name": name, "age": age, "birthday": birthYear, "year_taken": yearTaken, "isMale": gender,
                     "face_location": faceLocation, "face_score": faceScore, "second_face": faceScore2, "path": path,
                     "image_format":imFormat, "image_height":imHeight, "image_width":imWidth, "image_resolution":imRes}
        # remove bad data
        df = pd.DataFrame(dataTable)
        if combinedDf is None:
            combinedDf = df
        else:
            combinedDf = pd.concat([combinedDf, df])
    return _filterDataframe(combinedDf, ageRange, minScore, minRes, filterGender, filterRGB, filterMult)

"""
Helper function to filter csv dataset
Broke out so it can be used without regenerating dataframe every time

Params
    csvData: unfiltered csv pandas dataframe
    agetRange:  a vector containing the min and max age to keep. Helps trim out outlier errors in the dataset
    minScore:   the minimum face score to keep. Removes bad quality data
    minRes:     the minimum resolution image to keep
    filterGender:   a bool that determines whether to trim out faces with unlabeled geneders
    filterRGB:  determines whether we should filter out b/w images (or other encodings)
    filterMult: determines whether images with multiple faces should be filtered out
    indexPath: if specified, will delete the old index and generate a new one

Returns
    0: the filtered dataframe
"""
def _filterDataframe(csvData, ageRange, minScore, minRes, filterGender, filterRGB, filterMult, indexPath=None):
    numLeft = len(csvData.index)
    print(numLeft, " images found")
    if minScore is not None:
        csvData = csvData[csvData.face_score > minScore]
        numLeft = len(csvData.index)
        print("filtered low quality faces: ", numLeft, " images remaining")
    if minRes is not None:
        csvData = csvData[csvData.image_resolution > minRes]
        numLeft = len(csvData.index)
        print("filtered low res images: ", numLeft, " images remaining")
    if ageRange is not None:
        csvData = csvData[csvData.age > ageRange[0]]
        csvData = csvData[csvData.age < ageRange[1]]
        numLeft = len(csvData.index)
        print("filtered bad ages: ", numLeft, " images remaining")
    if filterGender:
        csvData = csvData[csvData.isMale.notnull()]
        numLeft = len(csvData.index)
        print("filtered null sex: ", numLeft, " images remaining")
    if filterRGB:
        csvData = csvData[csvData.image_format == "RGB"]
        numLeft = len(csvData.index)
        print("filtered non-RGB images: ", numLeft, " images remaining")
    if filterMult:
        csvData = csvData[csvData.second_face.isnull()]
        numLeft = len(csvData.index)
        print("filtered out multiple faces: ", numLeft, " images remaining")
    if indexPath is not None:
        print ("creating new index file")
        os.remove(indexPath)
        indices = createIndices(csvdata)
        file = open(indexPath, "wb")
        pickle.dump(indices, file)
        file.close()
    return csvData

"""
creates files that contain a list of indices for each category we are training on.
returns a dictionary with 3 keys: "Men", "Women" and "AgeBunLimits"
AgeBinLimits contains a list of cut-off points that define each age range
Men and Women contains a list of lists, where each element represents an age bin,
and contains a list of indices of images that fall into that bin

Params
    csvdata:      the dataframe of the .csv file of good quality faces we are working with
    ageRangeLimits: a vector describing all the age ranges we are breaking the data into
                    each item describes the ages < this value that will belong in this bin

Returns:
    0:  a dictionary containing the indices
"""
def createIndices(csvdata, ageRangeLimits=[20, 30, 40, 50, 60, 70, 80, 101]):
    numRows = len(csvdata.index)
    menArr = [[] for x in ageRangeLimits]
    womenArr = [[] for x in ageRangeLimits]
    for i in range(numRows):
        male = csvdata["isMale"][i] > 0.5
        age = csvdata["age"][i]
        binNum = 0
        for binLimit in ageRangeLimits:
            if age < binLimit:
                break
            else:
                binNum = binNum + 1
        if male:
            menArr[binNum] += [i]
        else:
            womenArr[binNum] += [i]
    resultDict = {"Men":menArr, "Women":womenArr, "AgeBinLimits":ageRangeLimits}
    return  resultDict

"""
Helper function to extract the next set of indices from the requested bin
Always returns numRequested indices, and handles looping back to the
beginning of the bin if necessary

Params
    binList:    the list of indices in this bin
    offset:     the offset to start grabbing indices from
    numRequested:   the number of indices to return

Returns
    0:  the list of indices extracted from the bin
    1:  the new offset we ended at
    2:  whether we passed over the end of the bin
"""
def _getFromBin(binList, offset, numRequested):
    startPt = offset
    endPt = min(startPt + numRequested, len(binList))
    returnList = binList[startPt:endPt]
    length = endPt - startPt
    looped = False
    while length < numRequested:
        looped = True
        startPt = 0
        endPt = min(numRequested - length, len(binList))
        returnList += binList[startPt:endPt]
        length = len(returnList)

    return returnList, endPt, looped

"""
Extracts a batch of images from the data. If the previous state is stored and
returned, the function can be called again to iterate through the data in batches

Params
    indices:    the indices dict for the data
    csvdata:    the pandas dataframe from the .csv of faces we are using
    numPerBin:  the number of images per category (age group/sex combination) we want to extract
    imageSize:  the size of the images to extract
    prevState:  the state containing the last indices we extracted, so we can get the next batch

Returns
    0:  a dictionary containing a vector for all the images (batchSize x imageSize),
        a vector of the ages (batchSize x 1), and a vector of the sexes (batchSize x 1) for the batch
    1:  the new state, whcih can be passed back in to get the next batch
    2:  a bool indicating whether we have visited all images at least one (since the start of the state)
"""
def getBatch(indices, csvdata, numPerBin=100, imageSize=250, prevState=None):
    ageBins = indices["AgeBinLimits"]
    numBins = len(ageBins)
    if prevState is None:
        prevState = np.zeros([numBins, 2, 2], dtype=int)
    batchIndices = np.zeros([numPerBin * numBins * 2], dtype=int)
    menLists = indices["Men"]
    womenLists = indices["Women"]
    lastIdx = 0
    for i in range(numBins):
        newMen, newOffset, didLoop = _getFromBin(menLists[i], prevState[i, 1, 0], numPerBin)
        batchIndices[lastIdx:lastIdx+numPerBin] = newMen
        prevState[i, 1, 0] = newOffset
        if didLoop:
            prevState[i, 1, 1] = 1
        lastIdx = lastIdx+numPerBin
        newWomen, newOffset, didLoop = _getFromBin(womenLists[i], prevState[i, 0, 0], numPerBin)
        batchIndices[lastIdx:lastIdx + numPerBin] = newWomen
        prevState[i, 0, 0] = newOffset
        if didLoop:
            prevState[i, 1, 0] = 1
        lastIdx = lastIdx + numPerBin
    imageArr = np.zeros([numPerBin * numBins * 2]+[imageSize, imageSize, 3], dtype=np.float32)
    sexArr = np.zeros([numPerBin * numBins * 2, 1], dtype=np.float32)
    ageArr = np.zeros([numPerBin * numBins * 2, 1], dtype=np.float32)
    i = 0
    for idx in batchIndices:
        path = csvdata["path"][idx]
        age = csvdata["age"][idx]
        sex = csvdata["isMale"][idx]
        image = imread(path)
        if image.shape != imageSize:
            image = imresize(image, [imageSize, imageSize, 3])
        if len(image.shape) == 2:
            image = np.resize(image, imageSize)
        # scale to [-1,1] range of tanh
        imageArr[i,:,:] = image / 255.0
        sexArr[i] = sex
        ageArr[i] = age / 100.0
        i = i + 1
    # scale to [-1,1] range of tanh
    imageArr = (imageArr * 2) - 1
    sexArr = (sexArr* 2) - 1
    ageArr = np.min((ageArr * 2) - 1, 1).reshape([-1, 1])
    didVisitAll = np.sum(prevState[:,:,1]) == numBins * 2
    return {"image":imageArr, "sex":sexArr, "age":ageArr}, prevState, didVisitAll


"""
scrables up the order of indices
this randomization is important, because we want to make sure batches aren't always the same
Params:
    indices:    the indices dict we want to randomize
"""
def _randomizeIndices(indices):
    menList = indices["Men"]
    womenList = indices["Women"]
    ageBins = indices["AgeBinLimits"]
    numBins = len(ageBins)
    for i in range(numBins):
        shuffle(menList[i])
        shuffle(womenList[i])



"""
Class to control data loading. benefits of using this class:
    -data is loaded on it's own thread,
    -data is stored in a buffer that can be pulled from
    -and a cache is supported so the first batch is loaded quickly from disk
    -data is randomized after each epoch
"""
class DataLoader(object):
    """"""

    """
    Initialize a DataLoader instance

    Params:
        indices:    the indices dict for the data
        csvData:    the pandas dataframe from the .csv of faces we are using
        numPerBin:  the number of images per category (age group/sex combination) we want to extract
        bufferMax:  the max size of the buffer that holds ready batches
        useCached:  if true, will try to load the first batch from disk to improve initial load time
    """
    def __init__(self, indices, csvData, numWorkerThreads=1, numPerBin=100, imageSize=100, bufferMax=5, useCached=True, debugLogs=False):
        self.imageSize=imageSize
        self.epochNum=0
        self.csvData = csvData
        self.numPerBin = numPerBin
        self.lock = threading.Condition()
        threadList = []
        for i in range(numWorkerThreads):
            threadIndex = deepcopy(indices)
            _randomizeIndices(threadIndex)
            newThread = threading.Thread(target=self._thread_runner, args=[threadIndex])
            newThread.daemon = True
            threadList += [newThread]
        self.threadList = threadList
        self.needsCache=False
        self.bufferMax = bufferMax
        self.buffer = []
        self.cachePath="./batch_cache.p"
        self.debug = debugLogs
        #if we are using caching, retore the old cache file, or mark that we need to generate one
        if useCached:
            if os.path.exists(self.cachePath):
                file = open(self.cachePath, "rb")
                self.buffer = pickle.load(file)
                file.close()
                #check to ensure size is right
                if self.buffer[0]["image"].shape[1] == imageSize and self.buffer[0]["image"].shape[0] % numPerBin == 0:
                    print("restored cache [" + str(len(self.buffer)) + " in buffer]")
                else:
                    self.needsCache = True
                    self.buffer = []
                    print("cached failed; wrong size")
            else:
                self.needsCache = True

    """
    this function is the internal thread that is run by the class
    continuously loads batches of data from disk, at puts them in the ready buffer
    """
    def _thread_runner(self, indices):
        currentState = None
        while(True):
            batchData, currentState, didFinish = getBatch(indices, self.csvData, numPerBin=self.numPerBin, prevState=currentState, imageSize=self.imageSize)
            self.lock.acquire()
            while len(self.buffer) >= self.bufferMax:
                self.lock.wait()
            self.buffer.append(batchData)
            if self.debug:
                print("Added Item [buffer size: " + str(len(self.buffer)) + "]")
            self.lock.notify()
            #generate cache file if necessary
            if self.needsCache:
                file = open(self.cachePath, "wb")
                pickle.dump( self.buffer, file)
                file.close()
                self.needsCache = False
            self.lock.release()
            if didFinish == True:
                # finished an entire epoch. Shuffle data, reset state
                self.epochNum = self.epochNum + 1
                currentState = None
                _randomizeIndices(indices)


    """
    start the data loading process
    """
    def start(self):
        for thread in self.threadList:
            thread.start()

    """
    Grab the next batch off the DataLoader's buffer

    Returns:
        0:  a dictionary containing:
                -a vector for all the images (batchSize x imageSize),
                -a vector of the ages (batchSize x 1),
                -a vector of the sexes (batchSize x 1) for the batch
    """
    def getData(self):
        self.lock.acquire()
        while len(self.buffer) == 0:
            print("[Empty Buffer. Waiting on an item]")
            self.lock.wait()
        nextBatch = self.buffer.pop(0)
        if self.debug:
            print("Removed Item [buffer size: " + str(len(self.buffer)) + "]")
        self.lock.notify()
        self.lock.release()
        return nextBatch

"""
Function to load the csv data and indices from disk, or create them if needed

Params
    datasetDir: the directory of the root of the IMDB-WIKI dataset
    csvPath:    the path of the csv representation of the data
                if no file exists at the path, a new one will be generated
    indicesPath:    the path of the indices from the data
                    if no file exists at the path, a new one will be generated

Returns
    0:  the csv data represented as a pandas dataframe
    1:  the index data
"""
def LoadFilesData(datasetDir, csvPath="./dataset.csv", indicesPath="./indices.p"):
    if os.path.exists(csvPath):
        print("restoring csv data...")
        csvdata = pd.read_csv(csvPath)
    else:
        print("creating " + csvPath + "...")
        csvdata = createCsv(datasetDir)
        csvdata.to_csv(csvPath, index=False, encoding='utf-8')
        print(csvPath + " saved")

    if os.path.exists(indicesPath):
        print("restoring indices data...")
        file = open(indicesPath, "rb")
        indices = pickle.load(file)
    else:
        print("creating " + indicesPath + "...")
        indices = createIndices(csvdata)
        file = open(indicesPath, "wb")
        pickle.dump(indices, file)
        print(indicesPath + " saved")
    file.close()
    _randomizeIndices(indices)
    return csvdata, indices



