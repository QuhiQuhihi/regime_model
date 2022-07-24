from ggs import *
import numpy as np
import matplotlib.pyplot as plt
import math


np.random.seed(0)
# Generate synthetic 1D data
# First 1000 samples: mean = 1, SD = 1
# Second 1000 samples: mean = 0, SD = 0.1
# Third 1000 samples: mean = 0, SD = 1
d1 = np.random.normal(1,1,1000)
d2 = np.random.normal(0,0.5,1000)
d3 = np.random.normal(-1,1,1000)

data = np.concatenate((d1,d2,d3))
data = np.reshape(data, (3000,1))

data = data.T #Convert to an n-by-T matrix

# Find up to 10 breakpoints at lambda = 1e-1
bps, objectives = GGS(data, Kmax = 10, lamb = 1e-1)

print bps
print objectives

# Plot objective vs. number of breakpoints. Note that the objective essentially
# stops increasing after K = 2, since there are only 2 "true" breakpoints
plotVals = range(len(objectives))
plt.plot(plotVals, objectives, 'or-')
plt.xlabel('Number of Breakpoints')
plt.ylabel(r'$\phi(b)$')
plt.show()


#Plot predicted Mean/Covs
breaks = bps[2]

mcs = GGSMeanCov(data, breaks, 1e-1)
predicted = []
varPlus = []
varMinus = []
for i in range(len(mcs)):
	for j in range(breaks[i+1]-breaks[i]):
		predicted.append(mcs[i][0]) # Estimate the mean
		varPlus.append(mcs[i][0] + math.sqrt(mcs[i][1][0])) # One standard deviation above the mean
		varMinus.append(mcs[i][0] - math.sqrt(mcs[i][1][0])) # One s.d. below

f, axarr = plt.subplots(2, sharex=True)
axarr[0].plot(data)
axarr[0].set_ylim([-4,4])
axarr[0].set_ylabel('Actual Data')
axarr[1].plot(predicted)
axarr[1].plot(varPlus, 'r--')
axarr[1].plot(varMinus, 'r--')
axarr[1].set_ylim([-4,4])
axarr[1].set_ylabel('Predicted mean (+/- 1 S.D.)')
plt.show()
