###################################################################################################
#
# GRBData.py
#
# Copyright (C) by Andreas Zoglauer.
# All rights reserved.
#
# Please see the file License.txt in the main repository for the copyright-notice.
#
###################################################################################################




###################################################################################################


import random 
import numpy as np
import ROOT as M
M.gSystem.Load("$(MEGALIB)/lib/libMEGAlib.so")


###################################################################################################


class GRBData:
  """
  This class performs energy loss training. A typical usage would look like this:

  AI = EventTypeIdentification("Ling2.seq3.quality.root", "Results", "TF:VOXNET", 1000000)
  AI.train()
  AI.test()

  """


###################################################################################################


  def __init__(self):
    """
    The default constructor for class EventClustering

    Attributes
    ----------
    FileName : string
      Data file name (something like: X.maxhits2.eventclusterizer.root)
    OutputPrefix: string
      Output filename prefix as well as outout directory name
    Algorithms: string
      The algorithms used during training. Seperate multiples by commma (e.g. "MLP,DNNCPU")
    MaxEvents: integer
      The maximum amount of events to use

    """

    self.OriginLatitude = 0
    self.OriginLongitude = 0
    
    self.Psi = np.zeros(shape=(0), dtype=int)
    self.Chi = np.zeros(shape=(0), dtype=int)
    self.Phi = np.zeros(shape=(0), dtype=int)
    
    self.Index = np.zeros(shape=(0), dtype=int)


###################################################################################################


  def getNumberOfEntries(self):
    return self.Psi.size


###################################################################################################

  def getEntry(self, Index):
    return self.Psi[Index], self.Chi[Index], self.Phi[Index]


###################################################################################################

  def getIndex(self, i):
    return self.Index[i]


###################################################################################################


  def create(self, ToyModel, NumberOfSourceEvents, NumberOfBackgroundEvents):
    """
    Switch between the various machine-learning libraries based on self.Algorithm
    """


    # Create a random rotation matrix
    V = M.MVector()
    V.SetMagThetaPhi(1, np.arccos(1 - 2*random.random()), 2.0 * np.pi * random.random())
    Angle = 2.0 * np.pi * random.random()

    '''
    if random.random() < 0.25:
      V.SetMagThetaPhi(1, 0.4, 0.1)
      Angle = 0.6
    elif random.random() < 0.5:
      V.SetMagThetaPhi(1, 0.9, 0.3)
      Angle = 4.6
    elif random.random() < 0.75:
      V.SetMagThetaPhi(1, 0.4, 0.8)
      Angle = 2.6
    else:
      V.SetMagThetaPhi(1, 0.2, 0.6)
      Angle = 0.2 
    '''
    
    Rotation = M.MRotation(Angle, V)
  
    # Retrieve the origin of the gamma rays
    Origin = M.MVector(0, 0, 1)
    Origin = Rotation*Origin
  
    self.OriginLatitude = Origin.Theta()
    self.OriginLongitude = Origin.Phi()
  
    self.Psi = np.zeros(shape=(NumberOfSourceEvents + NumberOfBackgroundEvents), dtype=int)
    self.Chi = np.zeros(shape=(NumberOfSourceEvents + NumberOfBackgroundEvents), dtype=int)
    self.Phi = np.zeros(shape=(NumberOfSourceEvents + NumberOfBackgroundEvents), dtype=int)
    self.Index = np.zeros(shape=(NumberOfSourceEvents + NumberOfBackgroundEvents), dtype=int)
  
    # Create the input source events
    for e in range(0, NumberOfSourceEvents):
      ChiBin, PsiBin, PhiBin, Index = ToyModel.createOneSourceDataSet(Rotation)
        
      self.Psi[e] = PsiBin
      self.Chi[e] = ChiBin
      self.Phi[e] = PhiBin
      self.Index[e] = Index
    
    # Create input background events
    for e in range(0, NumberOfBackgroundEvents):
      ChiBin, PsiBin, PhiBin, Index = ToyModel.createOneBackgroundDataSet()
    
      self.Psi[e + NumberOfSourceEvents] = PsiBin
      self.Chi[e + NumberOfSourceEvents] = ChiBin
      self.Phi[e + NumberOfSourceEvents] = PhiBin
      
      self.Index[e + NumberOfSourceEvents] = Index
      


