from ggs import *
import numpy as np
import matplotlib.pyplot as plt

# Read in daily log returns from 1997-2015 of 10 indices: 
# DM stocks, EM stocks, Real estate, Oil, Gold, HY bonds, EM HY bonds, GVT bonds, CORP bonds, IFL bonds
filename = "Data/Returns.txt"
data = np.genfromtxt(filename,delimiter=' ')
# Select DM stocks, Oil, and GVT bonds
feats = [0,3,7]

data = data.T #Convert to an n-by-T matrix


# Find 10 breakpoints at lambda = 1e-4
bps, objectives = GGS(data, Kmax = 10, lamb = 1e-4, features = feats)

# Find means and covariances of the segments, given the selected breakpoints
bp10 = bps[10] # Get breakpoints for K = 10
meancovs = GGSMeanCov(data, breakpoints = bp10, lamb = 1e-4, features = feats)


print("Breakpoints are at", bps)
print("Objectives are", objectives)

# Plot objective vs. number of breakpoints
plotVals = range(len(objectives))
plt.plot(plotVals, objectives, 'or-')
plt.xlabel('Number of Breakpoints')
plt.ylabel(r'$\phi(b)$')
plt.show()
