###################################################################################################
#
# ComptonTrackingGNN.py
#
# Copyright (C) by Andreas Zoglauer & 
# All rights reserved.
#
# Please see the file LICENSE in the main repository for the copyright-notice.
#
###################################################################################################



###################################################################################################


import tensorflow as tf
import numpy as np

#from mpl_toolkits.mplot3d import Axes3D
#import matplotlib.pyplot as plt

import random

import signal
import sys
import time
import math
import csv
import os
import argparse
from datetime import datetime
from functools import reduce

print("\nCompton Track Identification")
print("============================\n")



# Step 1: Input parameters
###################################################################################################


# Default parameters

UseToyModel = True

# Split between training and testing data
TestingTrainingSplit = 0.1

MaxEvents = 10



OutputDirectory = "Results"


parser = argparse.ArgumentParser(description='Perform training and/or testing of the event clustering machine learning tools.')
parser.add_argument('-f', '--filename', default='ComptonTrackIdentification.p1.sim.gz', help='File name used for training/testing')
parser.add_argument('-m', '--maxevents', default='10000', help='Maximum number of events to use')
parser.add_argument('-s', '--testingtrainingsplit', default='0.1', help='Testing-training split')
parser.add_argument('-b', '--batchsize', default='128', help='Batch size')

args = parser.parse_args()

if args.filename != "":
  FileName = args.filename

if int(args.maxevents) > 1000:
  MaxEvents = int(args.maxevents)

if int(args.batchsize) >= 16:
  BatchSize = int(args.batchsize)

if float(args.testingtrainingsplit) >= 0.05:
   TestingTrainingSplit = float(args.testingtrainingsplit)



if os.path.exists(OutputDirectory):
  Now = datetime.now()
  OutputDirectory += Now.strftime("_%Y%m%d_%H%M%S")

os.makedirs(OutputDirectory)



###################################################################################################
# Step 2: Global functions
###################################################################################################


# Take care of Ctrl-C
Interrupted = False
NInterrupts = 0
def signal_handler(signal, frame):
  global Interrupted
  Interrupted = True
  global NInterrupts
  NInterrupts += 1
  if NInterrupts >= 2:
    print("Aborting!")
    sys.exit(0)
  print("You pressed Ctrl+C - waiting for graceful abort, or press  Ctrl-C again, for quick exit.")
signal.signal(signal.SIGINT, signal_handler)


# Everything ROOT related can only be loaded here otherwise it interferes with the argparse
from EventData import EventData

# Load MEGAlib into ROOT so that it is usable
import ROOT as M
M.gSystem.Load("$(MEGALIB)/lib/libMEGAlib.so")
M.PyConfig.IgnoreCommandLineOptions = True



###################################################################################################
# Step 3: Create some training, test & verification data sets
###################################################################################################


# Read the simulation file data:
DataSets = []
NumberOfDataSets = 0

if UseToyModel == True:
  for e in range(0, MaxEvents):
    Data = EventData()
    Data.createFromToyModel()
    DataSets.append(Data)
    
    NumberOfDataSets += 1
    if NumberOfDataSets > 0 and NumberOfDataSets % 1000 == 0:
      print("Data sets processed: {}".format(NumberOfDataSets))
  
else:
  # Load geometry:
  Geometry = M.MDGeometryQuest()
  if Geometry.ScanSetupFile(M.MString(GeometryName)) == True:
    print("Geometry " + GeometryName + " loaded!")
  else:
    print("Unable to load geometry " + GeometryName + " - Aborting!")
    quit()


  Reader = M.MFileEventsSim(Geometry)
  if Reader.Open(M.MString(FileName)) == False:
    print("Unable to open file " + FileName + ". Aborting!")
    quit()


  print("\n\nStarted reading data sets")
  while True:
    Event = Reader.GetNextEvent()
    if not Event:
      break

    if Event.GetNIAs() > 0:
      Data = EventData()
      if Data.parse(Event) == True:
        Data.center()

        if Data.hasHitsOutside(XMin, XMax, YMin, YMax, ZMin, ZMax) == False and Data.isOriginInside(XMin, XMax, YMin, YMax, ZMin, ZMax) == True:
          DataSets.append(Data)
          NumberOfDataSets += 1

          if NumberOfDataSets > 0 and NumberOfDataSets % 1000 == 0:
            print("Data sets processed: {}".format(NumberOfDataSets))

    if NumberOfDataSets >= MaxEvents:
      break


print("Info: Parsed {} events".format(NumberOfDataSets))



# Split the data sets in training and testing data sets

# The number of available batches in the inoput data
NBatches = int(len(DataSets) / BatchSize)
if NBatches < 2:
  print("Not enough data!")
  quit()

# Split the batches in training and testing according to TestingTrainingSplit
NTestingBatches = int(NBatches*TestingTrainingSplit)
if NTestingBatches == 0:
  NTestingBatches = 1
NTrainingBatches = NBatches - NTestingBatches

# Now split the actual data:
TrainingDataSets = []
for i in range(0, NTrainingBatches * BatchSize):
  TrainingDataSets.append(DataSets[i])


TestingDataSets = []
for i in range(0,NTestingBatches*BatchSize):
   TestingDataSets.append(DataSets[NTrainingBatches * BatchSize + i])


NumberOfTrainingEvents = len(TrainingDataSets)
NumberOfTestingEvents = len(TestingDataSets)

print(np.unique(np.array([event.unique for event in TestingDataSets])))

print("Info: Number of training data sets: {}   Number of testing data sets: {} (vs. input: {} and split ratio: {})".format(NumberOfTrainingEvents, NumberOfTestingEvents, len(DataSets), TestingTrainingSplit))




###################################################################################################
# Step 4: Setting up the neural network
###################################################################################################


print("Info: Setting up the graph neural network...")


###################################################################################################
# Step 5: Training and evaluating the network
###################################################################################################


print("Info: Training and evaluating the network - to be written")



#input("Press [enter] to EXIT")
sys.exit(0)
