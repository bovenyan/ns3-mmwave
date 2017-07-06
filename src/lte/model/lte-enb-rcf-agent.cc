#include "lte-enb-rcf-agent.h"
#include <curl/curl.h>
#include "json.hpp"
#include <iostream>
// #include <ns3/log.h>

using nlohmann::json;
using std::cout; 
using std::endl;

size_t RESTcallback(void * contents, size_t size, size_t nmemb, string *s) {
    size_t new_length = size * nmemb;
    size_t old_length = s->size();

    try {
        s->resize(old_length + new_length);
    } catch (std::bad_alloc &e) {
        return 0;
    }

    std::copy((char*)contents, (char*)contents+new_length, s->begin()+old_length);
    return size*nmemb;
}

void SetCurlPOST(CURL * curl, const char * URL, string *response, string & jdump) {
    char errbuf[CURL_ERROR_SIZE] = { 0, };
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, URL);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, -1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jdump.c_str());
    curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, errbuf);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, RESTcallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response);
}

bool PerformCurl(CURL * curl) {
    CURLcode res;
    res = curl_easy_perform(curl);

    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n",
                curl_easy_strerror(res));
    }
    curl_easy_cleanup(curl);

    return res == CURLE_OK;
}

void SetCurlGET(CURL * curl, const char * URL, string *response) {
    char errbuf[CURL_ERROR_SIZE] = { 0, };
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_URL, URL);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, errbuf);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, RESTcallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response);
}

namespace ns3 {
//NS_LOG_COMPONENT_DEFINE ("LteEnbRCF");

RCFhoDecision::RCFhoDecision() {
    type = 0;
    subtype = 0;
    imsi = 0;
    oldCellId = 0;
    targetCellId = 0;
    toScheduleTime = 0;
    toCancelEvent = 0;
}

RCFadapter::RCFadapter() {
    curl = NULL;
}

bool RCFadapter::RESTresponseOK(const string & s) {
    json j = s;

    if (j["status"] == 0) {
        return true;
    }

    // TODO: error codes
    return false;
}

void RCFadapter::RCFsinrReport(int m_mmWaveCellId, std::map<uint64_t, double> sinrReport) {
    curl = curl_easy_init();

    if (curl) {
        json report;

        for (std::map<uint64_t, double>::iterator it = sinrReport.begin();
                it!=sinrReport.end(); ++it) {
            report.push_back(std::make_pair(it->first, it->second));
        }

        string response;
        std::stringstream ss; 
        ss << "http://127.0.0.1:5000/stats/report/";
        ss << m_mmWaveCellId;
        cout << ss.str()<<endl;
        string jdump = report.dump();

        cout<<jdump<<endl;

        SetCurlPOST(curl, ss.str().c_str(), &response, jdump);
        cout<<"CURL set finished"<<endl;
        PerformCurl(curl);

        // TODO: process return
    }
}


vector<RCFhoDecision> RCFadapter::RCFgetHoDecisionList(uint64_t queryTime, bool triggerOrUpdate) {
    curl = curl_easy_init();
    vector<RCFhoDecision> decisionList;

    if (curl) {
        CURLcode res;
        string response;

        json timestamp;
        timestamp["queryTime"] = queryTime;

        std::stringstream ss;
        ss << "http://127.0.0.1:5000/handover/";
        if (triggerOrUpdate) {
            ss<<"trigger";
        } else {
            ss<<"update";
        }
        string jdump = timestamp.dump();

        SetCurlPOST(curl, ss.str().c_str(), &response, jdump);
        PerformCurl(curl);

        json jResponse = json::parse(response);
        decisionList = jResponse.get<vector<RCFhoDecision> >();
    }

    return decisionList;
}

void RCFadapter::RCFeventScheduled(uint64_t imsi, uint16_t oldCellId, uint16_t targetCellId,
                                   uint64_t eventTs, uint32_t eventUid) {
    curl = curl_easy_init();

    if (curl) {
        json schedule;
        string response;

        schedule["oldCellId"] = oldCellId;
        schedule["targetCellId"] = targetCellId;
        schedule["eventTs"] = eventTs;
        schedule["eventUid"] = eventUid;

        std::stringstream ss;
        ss << "http://127.0.0.1:5000/handover/schedule/";
        ss << imsi;
        string jdump = schedule.dump();
        SetCurlPOST(curl, ss.str().c_str(), &response, jdump);
        PerformCurl(curl);
    }
}

void RCFadapter::RCFupdateStates(uint64_t imsi, bool m_mmWaveCellSetupCompletedUpdate,
                                 bool m_mmWaveCellSetupCompletedValue, bool m_lastMmWaveCellUpdate,
                                 uint16_t m_lastMmWaveCellValue, bool m_imsiUsingLteUpdate, bool m_imsiUsingLteValue) {
    curl = curl_easy_init();

    if (curl) {
        json statesUpdate;
        string response;

        if (m_mmWaveCellSetupCompletedUpdate) {
            statesUpdate["m_mmWaveCellSetupCompleted"] = m_mmWaveCellSetupCompletedValue;
        }
        if (m_lastMmWaveCellUpdate) {
            statesUpdate["m_lastMmWaveCell"] = m_lastMmWaveCellValue;
        }
        if (m_imsiUsingLteUpdate) {
            statesUpdate["m_imsiUsingLte"] = m_imsiUsingLteValue;
        }

        std::stringstream ss;
        ss << "http://127.0.0.1:5000/handover/statesupdate/";
        ss << imsi;
        string jdump = statesUpdate.dump();
        SetCurlPOST(curl, ss.str().c_str(), &response, jdump);
        PerformCurl(curl);
    }
}

RCFhoDecision RCFadapter::RCFconnBestMMwave(uint64_t imsi) {
    curl = curl_easy_init();
    RCFhoDecision decision;

    if (curl) {
        string response;

        std::stringstream ss;
        ss << "http://127.0.0.1:5000/handover/bestconn/";
        ss << imsi;
        string jdump = "";
        SetCurlPOST(curl, ss.str().c_str(), &response, jdump);
        PerformCurl(curl);

        json jResponse = json::parse(response);
        decision = jResponse.get<RCFhoDecision>();
    }

    return decision;
}

void RCFadapter::RCFinitializeLteEnbRRC(string handoverMode, double m_outageThreshold,
                                        double m_sinrThresholdDifference, int m_fixedTttValue, int m_minDynTttValue,
                                        int m_maxDynTttValue, double m_minDiffTttValue, double m_maxDiffTttValue,
                                        int m_cellId, bool m_interRatHoMode) {
    curl = curl_easy_init();

    if (curl) {
        json config;
        string response;

        config["handoverMode"] = handoverMode;
        config["m_outageThreshold"] = m_outageThreshold;
        config["m_sinrThresholdDifference"] = m_sinrThresholdDifference;
        config["m_fixedTttValue"] = m_fixedTttValue;
        config["m_minDynTttValue"] = m_minDynTttValue;
        config["m_maxDynTttValue"] = m_maxDynTttValue;
        config["m_minDiffTttValue"] = m_minDiffTttValue;
        config["m_maxDiffTttValue"] = m_maxDiffTttValue;
        config["m_cellId"] = m_cellId;
        config["m_interRatHoMode"] = m_interRatHoMode;

        std::string s("http://127.0.0.1:5000/lteenb/init");
        string jdump = config.dump();
        cout <<"DEBUG: CURL "<<  jdump << endl;

        SetCurlPOST(curl, s.c_str(), &response, jdump);
        PerformCurl(curl);

        json jResponse = json::parse(response);
    }
}

}


namespace nlohmann {
template <typename X, typename Y>
void adl_serializer<std::pair<X,Y> >::to_json(json& j, const std::pair<X,Y> & pa) {
    j.push_back(pa.first);
    j.push_back(pa.second);
}
template <typename X, typename Y>
void adl_serializer<std::pair<X,Y> >::from_json(const json& j, std::pair<X,Y> & pa) {
    pa.first = j[0];
    pa.second = j[1];
}

void to_json(json& j, const ns3::RCFhoDecision & ha) {
    j = json{{"type", ha.type}, {"imsi", ha.imsi},
        {"oldCellId", ha.oldCellId}, {"targetCellId", ha.targetCellId},
        {"toScheduleTime", ha.toScheduleTime},
        {"toCancelEvent", ha.toCancelEvent} };
}

void from_json(const json& j, ns3::RCFhoDecision & ha) {
    ha.type = j.at("type").get<int>();
    ha.subtype = j.at("subtype").get<int>();
    ha.imsi = j.at("imsi").get<uint64_t>();
    ha.oldCellId = j.at("oldCellId").get<uint16_t>();
    ha.targetCellId = j.at("targetCellId").get<uint16_t>();
    ha.toScheduleTime = j.at("toScheduleTime").get<uint64_t>();
    ha.toCancelEvent = j.at("toCancelEvent").get<uint32_t>();
}
}
