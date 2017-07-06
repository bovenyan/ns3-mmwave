from math import log10
from collections import defaultdict,deque
import logging

class handoverDecision():
    def __init__(self, Type, imsi, oldCellId, targetCellId):
        self.type = Type
        self.subtype = 0
        self.imsi = imsi
        self.oldCellId = oldCellId
        self.targetCellId = targetCellId
        self.toScheduleTime = 0 
        self.toCancelEvent = -1 


    def serialize(self):
        return {"type": self.type, 
                "subtype": self.subtype,
                "imsi": self.imsi,
                "oldCellId": self.oldCellId,
                "targetCellId": self.targetCellId,
                "toScheduleTime": self.toScheduleTime,
                "toCancelEvent": self.toCancelEvent}

class rcf_dual_conn():
    def __init__(self):
        # for LTE eNBs
        self.m_cellSinrMap = defaultdict()                          # int -> (int->double)  XX
        self.m_numNewSinrReports = 0                                #                       XX
        self.m_imsiCellSinrMap = defaultdict()                      # int -> (int->double)  XX RD not clear
        self.m_bestMmWaveCellForImsiMap = defaultdict(int)          # int -> int            XX RD not clear
        self.m_lastMmWaveCell = defaultdict(int)                    # int -> int            XX RD not clear
        self.m_mmWaveCellSetupCompleted = defaultdict(bool)         # int -> bool           XX
        self.m_imsiUsingLte = defaultdict(bool)                     # int -> bool           XX

        self.m_handoverMode = None                                  #

        # TTT based handover management
        self.m_imsiHandOverEventsMap = defaultdict(list)            # int -> [source, target, eventId, eventTs]

        self.m_outageThreshold = 0.0
        self.m_sinrThresholdDifference = 0.0
        
        self.m_fixedTttValue = 0
        self.m_minDynTttValue = 0
        self.m_maxDynTttValue = 0
        self.m_minDiffTttValue = 0.0
        self.m_maxDiffTttValue = 0.0

        # Cell identifier. Must be unique across the simulation.
        self.m_cellId = 0
        self.m_interRatHoMode = False 
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def initialize(self, content):
        self.m_handoverMode = content["handoverMode"]
        self.m_outageThreshold = content["m_outageThreshold"]
        self.m_sinrThresholdDifference = content["m_sinrThresholdDifference"]
        self.m_interRatHoMode = content["m_interRatHoMode"]
        
        self.m_fixedTttValue = content["m_fixedTttValue"]
        self.m_minDynTttValue = content["m_minDynTttValue"]
        self.m_maxDynTttValue = content["m_maxDynTttValue"]
        self.m_minDiffTttValue = content["m_minDiffTttValue"]
        self.m_maxDiffTttValue = content["m_maxDiffTttValue"]
        
    def DoRecvUeSinrUpdate(self, mmWaveCellId, ueImsiSinrMap):
        # update and add the entry
        # debug 
        # print "ueImsiSinr: " + str(ueImsiSinrMap)
        self.m_cellSinrMap[mmWaveCellId] = ueImsiSinrMap
        self.m_numNewSinrReports += 1

        # cycle on all the Imsi whose SINR is known in cell mmWaveCellId
        for imsi in ueImsiSinrMap:
            sinr = ueImsiSinrMap[imsi]
            # deleted m_notifyMmWaveSinrTrace(imsi, mmWaveCellId, sinr);
            # insert the entry
            if not (imsi in self.m_imsiCellSinrMap):
                self.m_imsiCellSinrMap[imsi] = defaultdict(float)
            # update the SINR measure or insert new measure
            self.m_imsiCellSinrMap[imsi][mmWaveCellId] = sinr

    def ComputeTtt(self, sinrDifference):
        if (self.m_handoverMode == "FIXED_TTT"):
            return self.m_fixedTttValue
        elif (self.m_handoverMode == "DYNAMIC_TTT"):
            if (sinrDifference < self.m_minDiffTttValue):
                return self.m_maxDynTttValue
            elif (sinrDifference > self.m_maxDynTttValue):
                return self.m_minDynTttValue
            else: # in between
                ttt = self.m_maxDynTttValue - self.m_minDynTttValue
                ttt = ttt * (sinrDifference - self.m_minDiffTttValue)
                ttt = ttt / (self.m_maxDiffTttValue - self.m_minDiffTttValue)
                ttt = self.m_maxDynTttValue - ttt 

                if (ttt < 0):
                    # Assert ttt < 0
                    pass
                
                truncated_ttt = int(ttt) & 256
                return truncated_ttt
        else:
            # Assert Unsupported HO mode 
            pass

    def ThresholdBasedSecondCellHandover(self, imsi, sinrDifference, maxSinrCellId, maxSinrDb):
        alreadyAssociatedImsi = False
        onHandoverImsi = True

        """
        On RecvRrcConnectionRequest for a new RNTI, the Lte Enb RRC stores the imsi
        of the UE and insert a new false entry in m_mmWaveCellSetupCompleted.
        After the first connection to a MmWave eNB, the entry becomes true.
        When an handover between MmWave cells is triggered, it is set to false.
        """

        if (imsi in self.m_mmWaveCellSetupCompleted):
            alreadyAssociatedImsi = True
            onHandoverImsi = not self.m_mmWaveCellSetupCompleted[imsi]
        else:
            alreadyAssociatedImsi = False
            onHandoverImsi = True

        if (maxSinrCellId == self.m_bestMmWaveCellForImsiMap[imsi] and 
                not self.m_imsiUsingLte[imsi]):
            if (alreadyAssociatedImsi and not onHandoverImsi and 
                    self.m_lastMmWaveCell[imsi] != maxSinrCellId and
                    sinrDifference > self.m_sinrThresholdDifference):
                self.m_mmWaveCellSetupCompleted[imsi] = False
                self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId

                HOdecision = handoverDecision(2, imsi, 
                        self.m_lastMmWaveCell[imsi], maxSinrCellId)
                return HOdecision.serialize()
            elif (alreadyAssociatedImsi and not onHandoverImsi
                    and self.m_lastMmWaveCell[imsi] != maxSinrCellId 
                    and sinrDifference < self.m_sinrThresholdDifference):
                pass
        else:
            if (alreadyAssociatedImsi and not onHandoverImsi): 
                if (self.m_imsiUsingLte[imsi]):
                    if self.m_lastMmWaveCell[imsi] == maxSinrCellId:
                        # it is on LTE, but now the last used MmWave cell is not in outage
                        self.m_imsiUsingLte[imsi] = False
                        
                        HOdecision = handoverDecision(3, imsi, 0, maxSinrCellId)
                        return HOdecision.serialize() 
                    else:
                        # it is on LTE, but now a MmWave cell different from the last used 
                        # is not in outage, so we need to handover
                        # already using LTE connection
                        self.m_mmWaveCellSetupCompleted[imsi] = False
                        HOdecision = handoverDecision(4, imsi, self.m_lastMmWaveCell[imsi], 
                                maxSinrCellId)
                        return HOdecision.serialize() 
                elif (self.m_lastMmWaveCell[imsi] != maxSinrCellId):
                    if (sinrDifference > self.m_sinrThresholdDifference):
                        # not on LTE, handover between MmWave cells
                        # The new secondary cell HO procedure does not require to switch to LTE
                        HOdecision = handoverDecision(2, imsi, self.m_lastMmWaveCell[imsi],
                                maxSinrCellId)
                        self.m_mmWaveCellSetupCompleted[imsi] = False
                        return HOdecision.serialize()
                    else:
                        self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId

    def ThresholdBasedInterRatHandover(self, imsi, sinrDifference, maxSinrCellId, maxSinrDb):
        alreadyAssociatedImsi = False;
        onHandoverImsi = True;
        """
        On RecvRrcConnectionRequest for a new RNTI, the Lte Enb RRC stores the imsi
        of the UE and insert a new false entry in m_mmWaveCellSetupCompleted.
        After the first connection to a MmWave eNB, the entry becomes true.
        When an handover between MmWave cells is triggered, it is set to false.
        """

        if (imsi in self.m_mmWaveCellSetupCompleted):
            alreadyAssociatedImsi = True
            onHandoverImsi = not self.m_mmWaveCellSetupCompleted[imsi]
        else:
            alreadyAssociatedImsi = False
            onHandoverImsi = True

        if (maxSinrCellId == self.m_bestMmWaveCellForImsiMap[imsi] and not self.m_imsiUsingLte):
            if (alreadyAssociatedImsi and not onHandoverImsi
                    and self.m_lastMmWaveCell[imsi] != maxSinrCellId):
                if (sinrDifference > self.m_sinrThresholdDifference):
                    self.m_mmWaveCellSetupCompleted[imsi] = False
                    self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId
                    HOdecision = handoverDecision(2, imsi, self.m_lastMmWaveCell[imsi], 
                            maxSinrCellId)
                    return HOdecision.serialize()
                else:
                    return None
        elif (alreadyAssociatedImsi and not onHandoverImsi):
            if (self.m_imsiUsingLte[imsi]): 
                # it is on LTE, but now the a MmWave cell is not in outage
                # switch back to MmWave
                self.m_mmWaveCellSetupCompleted[imsi] = False
                self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId
                HOdecision = handoverDecision(11, imsi, 0, maxSinrCellId)
                return HOdecision.serialize()

            elif (self.m_lastMmWaveCell[imsi] != maxSinrCellId):
                if (sinrDifference > self.m_sinrThresholdDifference):
                    HOdecision = handoverDecision(12, imsi, self.m_lastMmWaveCell[imsi], maxSinrCellId)
                    self.m_mmWaveCellSetupCompleted[imsi] = False
                    return HOdecision.serialize()
                else:
                    self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId
                    return None

    def TttBasedHandover(self, queryTime, imsi, cellSinrMap, sinrDifference, 
            maxSinrCellId, maxSinrDb):
        HOdecision = None
        alreadyAssociatedImsi = False
        onHandoverImsi = True

        if (imsi in self.m_mmWaveCellSetupCompleted):
            alreadyAssociatedImsi = True
            onHandoverImsi = not self.m_mmWaveCellSetupCompleted[imsi] 
        else:
            alreadyAssociatedImsi = False
            onHandoverImsi = True

        handoverNeeded = False

        currentSinrDb = 0
        if (alreadyAssociatedImsi and imsi in self.m_lastMmWaveCell):
            currentSinr = self.m_imsiCellSinrMap[imsi][self.m_lastMmWaveCell[imsi]]
            if (currentSinr == 0):
                currentSinrDb = float('-inf')
            else:
                currentSinrDb = 10 * log10(currentSinr)

        # the UE was in outage, now a mmWave eNB is available. It may be the one to which the UE 
        # is already attached or another one
        if (alreadyAssociatedImsi and self.m_imsiUsingLte[imsi]):
            if (not self.m_interRatHoMode):
                if (not onHandoverImsi):
                    if (self.m_lastMmWaveCell[imsi] == maxSinrCellId):
                        # it is on LTE, but now the last used MmWave cell is not in outage
                        # switch back to MmWave
                        HOdecision = handoverDecision(3, imsi, 0, maxSinrCellId)
                    else:
                        # it is on LTE, but now a MmWave cell different from the last used 
                        # is not in outage, so we need to handover
                        # already using LTE connection
                        # trigger ho via X2
                        self.m_mmWaveCellSetupCompleted[imsi] = False
                        HOdecision = handoverDecision(4, imsi, self.m_lastMmWaveCell[imsi],
                                maxSinrCellId)
                    
                    return HOdecision.serialize() 

                HOdecision = handoverDecision(3, imsi, 0, maxSinrCellId)
                HOdecision.subtype = 1

                return HOdecision.serialize()
            else:
                if (not onHandoverImsi):
                    self.m_mmWaveCellSetupCompleted[imsi] = False
                    self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId
                    HOdecision = handoverDecision(5, imsi, 0, maxSinrCellId)
                    return HOdecision.serialize()

        elif alreadyAssociatedImsi and not onHandoverImsi:
            # the UE is connected to a mmWave eNB which was not in outage
            # check if there are HO events pending

            HOdecision = handoverDecision(6, imsi, self.m_lastMmWaveCell[imsi], maxSinrCellId)

            if (imsi in self.m_imsiHandOverEventsMap): # handover event
                handoverEvent = self.m_imsiHandOverEventsMap[imsi]
                # an handover event is already scheduled
                # check if the cell to which the handover should happen is maxSinrCellId
                if (handoverEvent[1] == maxSinrCellId):
                    if (currentSinrDb < self.m_outageThreshold):
                        handoverNeeded = True
                        HOdecision.toCancelEvent = handoverEvent[2]
                        del self.m_imsiHandOverEventsMap[imsi] 
                    else:
                        newTtt = self.ComputeTtt(sinrDifference)
                        handoverHappensAtTime = handoverEvent[3]
                       
                        if (queryTime/1e6 + newTtt < handoverHappensAtTime/1e6):
                            HOdecision.toCancelEvent = handoverEvent[2]
                            del self.m_imsiHandOverEventsMap[imsi] 
                            handoverNeeded = True
                        # Check events and selectively cancel
                else:
                    targetCellId = handoverEvent[1]
                    originalTargetSinrDb = 10*log10(self.m_imsiCellSinrMap[imsi][targetCellId])

                    if (maxSinrDb - originalTargetSinrDb > self.m_sinrThresholdDifference):
                        HOdecision.toCancelEvent = handoverEvent[2]
                        
                        if (maxSinrCellId != self.m_lastMmWaveCell[imsi]):
                            handoverNeeded = True
                        else:
                            del self.m_imsiHandOverEventsMap[imsi]
                    else:
                        if (maxSinrCellId == self.m_lastMmWaveCell[imsi]):
                            HOdecision.toCancelEvent = handoverEvent[2]
                            del self.m_imsiHandOverEventsMap[imsi]
                        else:
                            pass
            else:
                if (maxSinrCellId != self.m_lastMmWaveCell[imsi]):
                    handoverNeeded = True

        if (handoverNeeded):
            millisecondsToHandover = self.ComputeTtt(sinrDifference)
            
            if (currentSinrDb < self.m_outageThreshold):
                millisecondsToHandover = 0

            if imsi in self.m_imsiHandOverEventsMap:
                HOdecision.toCancelEvent = self.m_imsiHandOverEventsMap[imsi][2] 
                del self.m_imsiHandOverEventsMap[imsi]

            HOdecision.toScheduleTime = millisecondsToHandover
            HOdecision.sourceCellId = self.m_lastMmWaveCell[imsi]
            HOdecision.targetCellId = maxSinrCellId

        if (HOdecision is None):
            return None
        else:
            return HOdecision.serialize()

    def TriggerUeAssociationUpdate(self, queryTime):
        handoverDecisionList = []

        for imsi in self.m_imsiCellSinrMap:
            maxSinr = 0.0
            currentSinr = 0.0
            maxSinrCellId = 0
            alreadyAssociatedImsi = False
            onHandoverImsi = True

            """
            If the LteEnbRrc is InterRatHo mode, the MmWave eNB notifies the 
            LTE eNB of the first access of a certain imsi. This is stored in a map
            and m_mmWaveCellSetupCompleted for that imsi is set to true.
            When an handover between MmWave cells is triggered, it is set to false.
            """
            if (imsi in self.m_mmWaveCellSetupCompleted):
                alreadyAssociatedImsi = True
                onHandoverImsi = not (self.m_mmWaveCellSetupCompleted[imsi])
            else:
                alreadyAssociatedImsi = False
                onHandoverImsi = True

            cellSinrMap = self.m_imsiCellSinrMap[imsi]

            print self.m_lastMmWaveCell
            for cellId, sinr in cellSinrMap.iteritems():
                if (sinr > maxSinr):
                    maxSinr = sinr
                    maxSinrCellId = cellId

                if self.m_lastMmWaveCell[imsi] == cellId:
                    currentSinr = sinr

            sinrDifference = 0
            currentSinrDb = 0
            if (currentSinr == 0):
                sinrDifference = float('inf')
                currentSinrDb = float('-inf')
            else:
                sinrDifference = abs(10*(log10(maxSinr) - log10(currentSinr)))
                currentSinrDb = 10 * log10(currentSinr)

            maxSinrDb = 10 * log10(maxSinr)

            self.logger.info("MaxSinr " + str(maxSinrDb) + 
                    " in cell " + str(maxSinrCellId) +  
                    " current cell " + str(self.m_lastMmWaveCell[imsi]) +
                    " currentSinrDb " + str(currentSinrDb) + 
                    " sinrDifference " + str(sinrDifference))

            # mmWave outage or currently using Lte but no mmwave are good 
            if ( maxSinrDb < self.m_outageThreshold or 
                    (self.m_imsiUsingLte[imsi] and maxSinrDb < m_outageThreshold + 2)):
                self.logger.info("----- Warn: outage detected ------ at time " + str(queryTime/10e9)) 
                if (not m_imsiUsingLte[imsi]):
                    # handover from mmwave to lte
                    if (not onHandoverImsi):
                        self.m_imsiUsingLte[imsi] = True
                        HOdecision = handoverDecision(1, imsi, 0, 0)
                        
                        # delete the handover event which was scheduled for this UE (if any)
                        if (imsi in self.m_imsiHandOverEventsMap):
                            HOdecision.toCancelEvent = self.m_imsiHandOverEventsMap[imsi]

                        handoverDecisionList.append(HOdecision.serialize())
                else:
                    # already on lte
                    pass

            else:   # at least a MmWave eNB can server 
                if (self.m_handoverMode == 'THRESHOLD'):
                    HOdecisionArray = self.ThresholdBasedSecondCellHandover(imsi, sinrDifference, 
                            maxSinrCellId, maxSinrDb)
                    if not (HOdecisionArray is None):
                        handoverDecisionList.append(HOdecisionArray)
                elif (self.m_handoverMode == 'FIXED_TTT' or 
                        self.m_handoverMode == 'DYNAMIC_TTT'):
                    self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId
                    HOdecisionArray = self.TttBasedHandover(queryTime, imsi, cellSinrMap, 
                            sinrDifference, maxSinrCellId, maxSinrDb)
                    if not (HOdecisionArray is None):
                        handoverDecisionList.append(HOdecisionArray)
                else:
                    pass

        return handoverDecisionList

    def UpdateUeHandoverAssociation(self, queryTime):
        handoverDecisionList = []

        for imsi in self.m_imsiCellSinrMap:
            maxSinr = 0.0
            currentSinr = 0.0
            maxSinrCellId = 0
            alreadyAssociatedImsi = False
            onHandoverImsi = True

            """
            If the LteEnbRrc is InterRatHo mode, the MmWave eNB notifies the 
            LTE eNB of the first access of a certain imsi. This is stored in a map
            and m_mmWaveCellSetupCompleted for that imsi is set to true.
            When an handover between MmWave cells is triggered, it is set to false.
            """
            if (imsi in self.m_mmWaveCellSetupCompleted):
                alreadyAssociatedImsi = True
                onHandoverImsi = not (self.m_mmWaveCellSetupCompleted(imsi))
            else:
                alreadyAssociatedImsi = False
                onHandoverImsi = True

            cellSinrMap = self.m_imsiCellSinrMap[imsi]

            for cellId, sinr in cellSinrMap.iteritems():
                if (sinr > maxSinr):
                    maxSinr = sinr
                    maxSinrCellId = cellId

                if self.m_lastMmWaveCell[imsi] == sinr:
                    currentSinr = sinr

            sinrDifference = abs(10*(log10(maxSinr) - log10(currentSinr)))
            maxSinrDb = 10 * log10(maxSinr)
            currentSinrDb = 10 * log10 * log10(maxSinr)

            # mmWave outage or currently using Lte but no mmwave are good 
            if ( maxSinrDb < self.m_outageThreshold or 
                    (m_imsiUsingLte[imsi] and maxSinrDb < m_outageThreshold + 2)):
                if (not m_imsiUsingLte[imsi]):
                    # handover from mmwave to lte
                    HOdecision = handoverDecision(1, imsi, 0, 0)
                    HOdecision.subtype = 0

                    if (not onHandoverImsi):
                        self.m_imsiUsingLte[imsi] = True
                        HOdecision = handoverDecision(11, imsi, 
                                self.m_lastMmWaveCell[imsi], self.m_cellId)
                        self.m_mmWaveCellSetupCompleted[imsi] = False
                        HOdecision.subtype = 1
                    
                    if (imsi in self.m_imsiHandOverEventsMap):
                        # TODO: problematic
                        HOdecision.toCancelEvent = self.m_imsiHandOverEventsMap[imsi][2]
                        del self.m_imsiHandOverEventsMap[imsi]

                    handoverDecisionList.append(HOdecision.serialize())
                else:
                    # already on lte
                    pass

            else:   # at least a MmWave eNB can server 
                if (self.m_handoverMode == 'THRESHOLD'):
                    HOdecisionArray = self.ThresholdBasedInterRatHandover(imsi, sinrDifference, 
                            maxSinrCellId, maxSinrDb)
                    if not (HOdecisionArray is None):
                        handoverDecisionList.append(HOdecisionArray)
                elif (self.m_handoverMode == 'FIXED_TTT' or 
                        self.m_handoverMode == 'DYNAMIC_TTT'):
                    self.m_bestMmWaveCellForImsiMap[imsi] = maxSinrCellId
                    HOdecisionArray = self.TttBasedHandover(queryTime, imsi, cellSinrMap, 
                            sinrDifference, maxSinrCellId, maxSinrDb)
                    if not (HOdecisionArray is None):
                        handoverDecisionList.append(HOdecisionArray)
                else:
                    pass

        return handoverDecisionList
    
    def RCFupdateStates(self, imsi, m_mmWaveCellSetupCompletedVal, m_lastMmWaveCellVal, m_imsiUsingLteVal):
        if (not m_mmWaveCellSetupCompletedVal is None):
            self.m_mmWaveCellSetupCompleted[imsi] = m_mmWaveCellSetupCompletedVal
        if (not m_lastMmWaveCellVal is None):
            self.m_lastMmWaveCell[imsi] = m_lastMmWaveCellVal
        if (not m_imsiUsingLteVal is None):
            self.m_imsiUsingLte[imsi] = m_imsiUsingLteVal

    def RCFconnBestMmWave(self, imsi):
        HOdecision = handoverDecision(0, 0, 0, 0)

        if (self.m_cellId != self.m_bestMmWaveCellForImsiMap[imsi]):
            maxSinrCellId = self.m_bestMmWaveCellForImsiMap[imsi]
            maxSinrDb = 10*log10(self.m_imsiCellSinrMap[imsi][maxSinrCellId])

            if (maxSinrDb > self.m_outageThreshold):
                HOdecision = handoverDecision(21, imsi, 0, maxSinrCellId)
                return HOdecision.serialize()
            else:
                self.m_imsiUsingLte[imsi] = True
                HOdecision = handoverDecision(22, imsi, 0, 0)
                return HOdecision.serialize()

        return HOdecision.serialize()
