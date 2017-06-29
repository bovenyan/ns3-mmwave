#ifndef LTE_ENB_RCF_AGENT_H
#define LTE_ENB_RCF_AGENT_H

#include <string> // RCF functions
#include <curl/curl.h>
#include <vector>
#include <map>
#include "json.hpp"

using std::string;
using std::vector;

namespace ns3 {
class RCFhoDecision {
public:
    // immediate/to schedule actions
    int type;
    int subtype;
    uint64_t imsi;
    uint16_t oldCellId;
    uint16_t targetCellId;
    uint64_t toScheduleTime; 
    uint32_t toCancelEvent;

    RCFhoDecision();
};

class RCFadapter {
private:
    CURL *curl;
    CURLcode res;

    bool RESTresponseOK(const string & s);

public:
    RCFadapter();

    void RCFinitializeLteEnbRRC(string handoverMode, double m_outageThreshold,
            double m_sinrThresholdDifference, int m_fixedTttValue, int m_minDynTttValue,
            int m_maxDynTttValue, double m_minDiffTttValue, double m_maxDiffTttValue,
            int m_cellId, bool m_interRatHoMode);
    void RCFsinrReport(int mmWaveCellId, std::map<uint64_t, double> sinrReport);
    vector<RCFhoDecision> RCFgetHoDecisionList(uint64_t queryTime, bool triggerOrUpdate);
    void RCFeventScheduled(uint64_t imsi, uint16_t oldCellId, uint16_t targetCellId,
            uint64_t eventTs, uint32_t eventUid);
    void RCFupdateStates(uint64_t imsi, bool m_mmWaveCellSetupCompletedUpdate, 
            bool m_mmWaveCellSetupCompletedValue, bool m_lastMmWaveCellUpdate, 
            uint16_t m_lastMmWaveCellValue, bool m_imsiUsingLteUpdate, bool m_imsiUsingLteUpdateValue);
    RCFhoDecision RCFconnBestMMwave(uint64_t imsi);
};

}

namespace nlohmann {
template <typename X, typename Y>
struct adl_serializer<std::pair<X,Y> > {
    static void to_json(json& j, const std::pair<X,Y> & pa); 
    static void from_json(const json& j, std::pair<X,Y> & pa); 
};

void to_json(json& j, const ns3::RCFhoDecision & ha); 
void from_json(const json& j, ns3::RCFhoDecision & ha); 
}

#endif
