###################################################################################################
#
# ComptonTrackingGNN.py
#
# Copyright (C) by Andreas Zoglauer & Pranav Nagarajan
# All rights reserved.
#
# Please see the file LICENSE in the main repository for the copyright-notice.
#
###################################################################################################



###################################################################################################

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

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

MaxEvents = 100000



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
    Data.createFromToyModel(e)
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

# Criterion for choosing to connect two nodes
radius = 20

# Checking if distance is within criterion
def distanceCheck(h1, h2):
    dist = np.sqrt(np.sum((h1 - h2)**2))
    return dist <= radius

# Creates the graph representation for the detector
def CreateGraph(event):

    adjacency = np.zeros((len(event.X), len(event.X)))

    data = np.array(list(zip(event.X, event.Y, event.Z, event.E, event.Type, event.Origin)))
    hits = data[:, :3].astype(np.float)
    energies = data[:, 3].astype(np.float)
    types = data[:, 4]
    origins = data[:, 5].astype(np.int)

    for i in range(len(hits)):
        for j in range(i+1, len(hits)):
            if types[i] == 'g' and types[j] == 'g' or distanceCheck(hits[i], hits[j]):
                adjacency[i][j] = adjacency[j][i] = 1

    # Create the incoming matrix, outgoing matrix, and matrix of labels
    num_edges = int(np.sum(adjacency))
    Ro = np.zeros((len(hits), num_edges))
    Ri = np.zeros((len(hits), num_edges))
    y = np.zeros((len(hits), len(hits)))

    # Fill in the incoming matrix, outgoing matrix, and matrix of labels
    for i in range(len(adjacency)):
        for j in range(len(adjacency[0])):
            if adjacency[i][j]:
                Ro[i, np.arange(num_edges)] = 1
                Ri[j, np.arange(num_edges)] = 1
                if i + 1 == origins[j]:
                    y[i][j] = 1

    # Generate feature matrix of nodes
    X = data[:, :4].astype(np.float)

    return [X, adjacency, Ro, Ri, y]


# Definition of edge network (calculates edge weights)
def EdgeNetwork(H, Ro, Ri, input_dim, hidden_dim):

    def create_B(H):
        bo = Ro.T @ H
        bi = Ri.T @ H
        B = tf.keras.layers.concatenate([bo, bi])
        return B

    B = tf.keras.layers.Lambda(lambda H: create_B(H))(H)
    layer_2 = tf.keras.layers.Dense(hidden_dim, activation = "tanh")(B)
    layer_3 = tf.keras.layers.Dense(1, activation = "sigmoid")(layer_2)

    return layer_3


# Definition of node network (computes states of nodes)
def NodeNetwork(H, Ro, Ri, edge_weights, input_dim, output_dim):

    def create_M(e):
        bo = Ro.T @ H
        bi = Ri.T @ H
        Rwo = Ro * tf.transpose(e)
        Rwi = Ri * tf.transpose(e)
        mi = Rwi @ bo
        mo = Rwo @ bi
        M = tf.keras.layers.concatenate([mi, mo, H])
        return M

    M = tf.keras.layers.Lambda(lambda e: create_M(e))(edge_weights)
    layer_4 = tf.keras.layers.Dense(output_dim, activation = "tanh")(M)
    layer_5 = tf.keras.layers.Dense(output_dim, activation = "tanh")(layer_4)

    return layer_5


# Definition of overall network (iterates to find most probable edges)
def SegmentClassifier(A, Ro, Ri, input_dim = 4, hidden_dim = 16, num_iters = 3):

    # Application of input network (creates latent representation of graph)
    input_layer = tf.keras.layers.Input(batch_shape = (len(Ro), input_dim))
    H = tf.keras.layers.Dense(hidden_dim, activation = "tanh")(input_layer)
    H = tf.keras.layers.concatenate([H, input_layer])

    # Application of graph neural network (generates probabilities for each edge)
    for i in range(num_iters):
        edge_weights = EdgeNetwork(H, Ro, Ri, input_dim + hidden_dim, hidden_dim)
        H = NodeNetwork(H, Ro, Ri, edge_weights, input_dim + hidden_dim, hidden_dim)
        H = tf.keras.layers.concatenate([H, input_layer])

    output_layer = EdgeNetwork(H, Ro, Ri, input_dim + hidden_dim, hidden_dim)

    # Fill in adjacency matrix with probabilities
    indices = np.nonzero(A.flatten())[0][:, None]
    output = tf.scatter_nd(indices, output_layer, [len(A.flatten()), 1])
    output = tf.reshape(output, [len(A), len(A[0])])

    # Creation and compilation of model
    model = tf.keras.models.Model(inputs = input_layer, outputs = output)
    model.compile(optimizer = 'adam', loss = 'categorical_crossentropy', metrics = ['accuracy'])
    print(model.summary())

    return model


###################################################################################################
# Step 5: Training and evaluating the network
###################################################################################################


print("Info: Training and evaluating the network - to be written")

for Batch in range(NTrainingBatches):
    for e in range(BatchSize):

        # Prepare graph for a set of simulated events (training)
        event = TrainingDataSets[Batch*BatchSize + e]
        X, A, Ro, Ri, y = CreateGraph(event)
        model = SegmentClassifier(A, Ro, Ri)

        # Fit the model to the data
        model.fit(X, y)

#for Batch in range(NTestingBatches):
#    for e in range(BatchSize):
#
#        # Prepare graph for a set of simulated events (testing)
#        event = TestingDataSets[Batch*BatchSize + e]
#        X, Ro, Ri, y = CreateGraph(event)
#
#        # Generate predictions for a graph
#        predicted_edge_weights = model.predict(X)


#input("Press [enter] to EXIT")
sys.exit(0)
