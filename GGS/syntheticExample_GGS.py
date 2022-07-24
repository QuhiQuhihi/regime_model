from ggs import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import math
from hmmlearn.hmm import GaussianHMM
from numpy.testing import assert_array_equal, assert_array_almost_equal
import time
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 
warnings.filterwarnings("ignore", category=RuntimeWarning)

d = 25 #d-dimensional covariance
numCovs = 10 #Number of segments
samplesPerSeg = 100

#Generate numCovs random covariances
runSum = 0
for z in range(100):
	np.random.seed(z)
	c = []
	for i in range(numCovs):
		temp = np.random.normal(size=(d,d))
		temp2 = np.dot(temp, temp.T)
		c.append(temp2)


	#Generate synthetic data

	data = np.zeros((numCovs*samplesPerSeg, d))
	for i in range(numCovs):
		for j in range(samplesPerSeg):
			temp = np.random.multivariate_normal(np.zeros(d), c[i])
			data[samplesPerSeg*i + j, :] = temp		

	data = data.T

	fname = "SynthData_"+str(z)+".txt"
	np.savetxt(fname, data, fmt='%f', delimiter=',')

	#Run GGS
	bps = GGS(data, Kmax = numCovs-1, lamb = 10)
	print bps[0][-1]