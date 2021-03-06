import  NeuralNet
from DataLoader import  LoadFilesData, DataLoader
from Visualization import visualizeImages
from math import ceil, sqrt
import numpy as np

"""
Generate a sample from the network

Params
    network:    the neural network to sample from
    sampleSize: the number of images to create
    gender:     optionally specify the gender(s) to generate. int, array, or None
    age:        optionally specify the age(s) to generate. int, array, or None
    saveName:   if specified, will save a visualization image grid using this name

Returns
    0:  a nupy array of the results generated
"""
def randomSample(network, sampleSize, gender=None, age=None, saveName=None):
    if gender is not None:
        genderVec = np.ones([sampleSize, 1]) * (gender != 0)
    else:
        genderVec = np.random.randint(2, size=sampleSize)
    if age is not None:
        ageVec = np.ones([sampleSize, 1]) * age
    else:
        ageVec = np.random.randint(15, 75, size=sampleSize)
    genderVec = ((genderVec * 2) - 1).astype(np.float32).reshape([-1, 1])
    ageVec = (((ageVec / 100.0) * 2) - 1).astype(np.float32).reshape([-1, 1])
    noiseVec = np.random.uniform(-1, 1, [sampleSize, network.noise_size]).astype(np.float32)
    samples =  network.getSample(noiseVec, genderVec, ageVec)
    if saveName is not None:
        numRows = int(ceil(sqrt(sampleSize)))
        visualizeImages(samples, numRows=numRows, fileName=saveName)
    return samples

"""
Generate a visualization showing the influence of the age variable
Creates a single row, where each column shows the age value increasing

Params
    network:    the neural network to sample from
    numAges:    the number of faces to generate
    minAge:     the lowest age value to use
    maxAge:     the largest age value to use
    gender:     optionally specify the gender(s) to generate. int, or None
    noiseArr:    the noise values to use, if a specific face is desired
    saveName:   if specified, will save a visualization image grid using this name

Returns
    0:  a nupy array of the results generated
"""
def ageSample(network, numAges, minAge=25, maxAge=75, gender=None, noiseArr=None, saveName=None):
    if gender is None:
        gender = np.random.randint(2, size=1)
    if noiseArr is None:
        noiseArr = np.random.uniform(-1, 1, [1, network.noise_size]).astype(np.float32)
    ageMat = (((np.linspace(minAge, maxAge, numAges, dtype=int) / 100.0) * 2) - 1).reshape([numAges, 1])
    genderMat = ((np.ones([numAges, 1]) * gender) * 2) - 1
    noiseMat = np.ones([numAges, network.noise_size]) * noiseArr
    samples = network.getSample(noiseMat, genderMat, ageMat)
    if saveName is not None:
        visualizeImages(samples, numRows=1, fileName=saveName)
    return samples

"""
Generate a visualization showing the influence of the age variable
Creates multiple rows, where each column shows the age value increasing
and each row is an individual face (noise value/gender)

Params
    network:    the neural network to sample from
    numAges:    the number of faces to generate
    numSamples: the number of unique individuals to generate
    minAge:     the lowest age value to use
    maxAge:     the largest age value to use
    gender:     optionally specify the gender(s) to generate. int, or None
    noiseArr:    the noise values to use, if a specific face is desired
    saveName:   if specified, will save a visualization image grid using this name

Returns
    0:  a nupy array of the results generated
"""
def ageSampleMultiple(network, numAges, numSamples, minAge=25, maxAge=75, saveName=None):
    combinedMat = np.zeros([numSamples*numAges, 64, 64, 3])
    for i in range(numSamples):
        result = ageSample(network, numAges, minAge=minAge, maxAge=maxAge, saveName=None)
        combinedMat[numAges*i:numAges*(i+1),:,:,:] = result
    if saveName is not None:
        visualizeImages(combinedMat, numRows=numSamples, fileName=saveName)
    return combinedMat

"""
Generate a visualization showing the influence of the sex variable
Creates two rows, with famles on the top row and males on the bottom,
and each column is an individual face (same noice vector and age value)

Params
    network:    the neural network to sample from
    numSamples: the number of individuals to generate
    age:        optionally specify the age(s) to generate. int or None
    saveName:   if specified, will save a visualization image grid using this name

Returns
    0:  a nupy array of the results generated
"""
def sexSample(network, numSamples, age=None, saveName=None):
    if age is not None:
        ageVec = np.ones([numSamples, 1]) * age
    else:
        ageVec = np.random.randint(15, 75, size=numSamples)
    ageVec = (((ageVec / 100.0) * 2) - 1).astype(np.float32).reshape([-1, 1])
    noiseArr = np.random.uniform(-1, 1, [numSamples, network.noise_size]).astype(np.float32)
    genderArr = np.array([0,1])


    noiseArr = np.concatenate([noiseArr, noiseArr])
    ageVec = np.concatenate([ageVec, ageVec])
    genderArr = genderArr.repeat(numSamples).reshape(numSamples*2, 1)

    samples = network.getSample(noiseArr, genderArr, ageVec)
    if saveName is not None:
        visualizeImages(samples, numRows=2, fileName=saveName)
    return samples

if __name__ == "__main__":
    # initialize the data loader
    image_size = 64
    batch_size = 64
    noise_size = 100

    # start training
    network = NeuralNet.NeuralNet(batch_size=batch_size, image_size=image_size, noise_size=noise_size, learningRate=5e-4)

    randomSample(network, 36, saveName="sample.png")
    ageSampleMultiple(network, 10, 3, saveName="age_sample.png")
    sexSample(network, 10, saveName="sex_sample.png")
