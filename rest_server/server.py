from flask import Flask, jsonify, request
from dual_connectivity import rcf_dual_conn

app = Flask(__name__)
rcf = rcf_dual_conn()

@app.route('/lteenb/init', methods=['POST'])
def initializeLTE():
    content = request.json
    if (isinstance(content, dict)):
        rcf.initialize(content)
    return jsonify([]);

@app.route('/stats/report/<int:mmWaveCellId>', methods=['POST'])
def reportMeasurement(mmWaveCellId):
    content = request.json
    if isinstance(content, list):
        # translate list into map
        ueImsiSinrMap = defaultdict(float)
        for key,val in content:
            ueImsiSinrMap[key] = val

        rcf.DoRecvUeSinrUpdate(mmWaveCellId, ueImsiSinrMap)
        return jsonify({'status': 0})
    else:
        return jsonify({'status': 1})

@app.route('/handover/action/trigger', methods=['POST'])
def getHandoverTrigger():
    content = request.json
    
    if ("queryTime" in content):
        queryTime = int(content["queryTime"])
        handoverDecisionList = rcf.TriggerUeAssociationUpdate(queryTime)
        return jsonify(handoverDecisionList)
    else:
        return jsonify([])

@app.route('/handover/action/update', methods=['POST'])
def getHandoverUpdate():
    content = request.json
    
    if ("queryTime" in content):
        queryTime = int(content["queryTime"])
        handoverDecisionList = rcf.UpdateUeHandoverAssociation(queryTime)
        return jsonify(handoverDecisionList)
    else:
        return jsonify([])

@app.route('/handover/schedule/<int:imsi>')
def scheduleEvent(imsi):
    content = request.json

    if (isinstance(content, dict)):
        rcf.RCFeventScheduled(imsi, content["oldCellId"], 
                content["targtCellId"], content["eventTs"],
                content["eventUid"])
        return jsonify([])
    else:
        return jsonify([])

@app.route('/handover/statesupdate/<int:imsi>')
def updateStates(imsi):
    content = request.json

    if (isinstance(content, dict)):
        imsi = content['imsi']
        m_mmWaveCellSetupCompletedVal = None
        m_lastMmWaveCellVal = None
        m_imsiUsingLteVal = None

        if ('m_mmWaveCellSetupCompleted' in content):
            m_mmWaveCellSetupCompletedVal = content['m_mmWaveCellSetupCompleted'] 
        if ('m_lastMmWaveCell' in content):
            m_lastMmWaveCellVal = content['m_lastMmWaveCell']
        if ('m_imsiUsingLte' in content):
            m_imsiUsingLteVal = content['m_imsiUsingLte']

        rcf.RCFupdateStates(imsi, m_mmWaveCellSetupCompletedVal, m_lastMmWaveCellVal, m_imsiUsingLteVal)

        return jsonify([])
    else:
        return jsonify([])

@app.route('/handover/bestconn/<int:imsi>')
def selBestConn(imsi):
    content = request.json
    HOdecision = rcf.RCFconnBestMmwave(imsi)
    return jsonify(HOdecision)

if __name__ == "__main__":
    app.run(port=5000)
