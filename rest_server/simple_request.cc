#include <stdio.h>
#include <curl/curl.h>
#include <vector>
#include <string>
#include <map>
#include <iostream>
#include "json.hpp"

using std::string; 
using std::cout;
using std::endl;
using std::vector;
using std::map;
using std::pair;
using nlohmann::json;

size_t rest_callback(void * contents, size_t size, size_t nmemb, string *s) {
    size_t new_length = size * nmemb;
    size_t old_length = s->size();

    try {
        s->resize(old_length + new_length);
    }
    catch (std::bad_alloc &e){
        return 0;
    }

    std::copy((char*)contents, (char*)contents+new_length, s->begin()+old_length);
    return size*nmemb;
} 

bool rest_response_verification(const string & s) {
    json j = s;

    if (j["status"] == 0){
        return true;
    }

    // TODO: error codes
    return false;
}

//size_t curl_callback_string(void * contents, size_t size, size_t nmemb, string *s){
//    size_t new_length = size * nmemb;
//    size_t old_length = s->size();
//
//    try {
//        s->resize(old_length + new_length);
//    }
//    catch (std::bad_alloc &e){
//        return 0;
//    }
//
//    std::copy((char*)contents, (char*)contents+new_length, s->begin()+old_length);
//    return size*nmemb;
//}

namespace ns {
    struct sinr_report{
        vector<double> content;
        //sinr_report(vector<double> & report){ content = report; };
    };

    void to_json(json& j, const sinr_report &p){
        j = json({{"ueImsiSinrMap", p.content}});
    }

    template <typename BasicJsonType>
    void from_json(const BasicJsonType & j, sinr_report & sr){
        json::iterator j_iter = j.begin();
        sr.content = j_iter.value().get<vector<double> >();
    }
}

static
void dump(const char *text,
          FILE *stream, unsigned char *ptr, size_t size)
{
  size_t i;
  size_t c;
  unsigned int width=0x10;
 
  fprintf(stream, "%s, %10.10ld bytes (0x%8.8lx)\n",
          text, (long)size, (long)size);
 
  for(i=0; i<size; i+= width) {
    fprintf(stream, "%4.4lx: ", (long)i);
 
    /* show hex to the left */
    for(c = 0; c < width; c++) {
      if(i+c < size)
        fprintf(stream, "%02x ", ptr[i+c]);
      else
        fputs("   ", stream);
    }
 
    /* show data on the right */
    for(c = 0; (c < width) && (i+c < size); c++) {
      char x = (ptr[i+c] >= 0x20 && ptr[i+c] < 0x80) ? ptr[i+c] : '.';
      fputc(x, stream);
    }
 
    fputc('\n', stream); /* newline */
  }
}

static
int my_trace(CURL *handle, curl_infotype type,
             char *data, size_t size,
             void *userp)
{
  const char *text;
  (void)handle; /* prevent compiler warning */
  (void)userp;
 
  switch (type) {
  case CURLINFO_TEXT:
    fprintf(stderr, "== Info: %s", data);
  default: /* in case a new one is introduced to shock us */
    return 0;
 
  case CURLINFO_HEADER_OUT:
    text = "=> Send header";
    break;
  case CURLINFO_DATA_OUT:
    text = "=> Send data";
    break;
  case CURLINFO_SSL_DATA_OUT:
    text = "=> Send SSL data";
    break;
  case CURLINFO_HEADER_IN:
    text = "<= Recv header";
    break;
  case CURLINFO_DATA_IN:
    text = "<= Recv data";
    break;
  case CURLINFO_SSL_DATA_IN:
    text = "<= Recv SSL data";
    break;
  }
 
  dump(text, stderr, (unsigned char *)data, size);
  return 0;
}

int main(void){
    CURL *curl;
    CURLcode res;
    string s;

    curl = curl_easy_init();
    if (curl) {
        // GET 
        //curl_easy_setopt(curl, CURLOPT_URL, "127.0.0.1:5000/stats/report");
        //curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_callback_string);
        //curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);
        //curl_easy_setopt(curl, CURLOPT_VERBOSE, 1L);

        //res = curl_easy_perform(curl);

        //if (res != CURLE_OK){
        //    fprintf(stderr, "curl_easy_perform() failed: %s\n",
        //            curl_easy_strerror(res));
        //}

        //curl_easy_cleanup(curl);
        
        // POST
        json content;
        // vector<double> vec;
        // vec.push_back(1.1);
        // vec.push_back(2);

        // ns::sinr_report sr;
        // sr.content = vec;

        map<string, double> sr;
        // vector<pair<int, double> > sr;
        //pair<int, double> vec(1, 0.1);
        // sr.push_back(vec);
        sr["1"] = 3.2;
        sr["4"] = 1.3;
        json j(sr);
        
        char errbuf[CURL_ERROR_SIZE] = { 0, };
        
        char agent[1024] = { 0, };
        snprintf(agent, sizeof agent, "libcurl/%s",
                curl_version_info(CURLVERSION_NOW)->version);
        agent[sizeof agent - 1] = 0;
        
        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Expect:");
        headers = curl_slist_append(headers, "Content-Type: application/json");
        
        // curl_easy_setopt(curl, CURLOPT_DEBUGFUNCTION, my_trace);

        // curl_easy_setopt(curl, CURLOPT_USERAGENT, agent);
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
		string jdump = j.dump();
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jdump.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, -1L);
        curl_easy_setopt(curl, CURLOPT_URL, "http://127.0.0.1:5000/stats/report/1");
        // curl_easy_setopt(curl, CURLOPT_VERBOSE, 1L);
        curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, errbuf);

        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, rest_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);

        res = curl_easy_perform(curl);

        if (res != CURLE_OK){ 
            fprintf(stderr, "curl_easy_perform() failed: %s\n",
                    curl_easy_strerror(res));
        }

        curl_easy_cleanup(curl);
    }

    cout<<s<<endl;
    cout<<"Program Finished"<<endl;

    return 0;
}
