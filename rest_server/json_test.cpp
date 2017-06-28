#include "json.hpp"
#include <iostream>

using nlohmann::json;
using std::cout;
using std::endl;
using std::pair;
using std::vector;

namespace nlohmann {
    template <typename X, typename Y>
    struct adl_serializer<std::pair<X,Y> >{
        static void to_json(json& j, const std::pair<X,Y> & pa){
            j.push_back(pa.first);
            j.push_back(pa.second); 
        }
        static void from_json(const json& j, std::pair<X,Y> & pa){
            pa.first = j[0];
            pa.second = j[1];
        }
    };
}

int main(){
    json j;
    //j[1] = 2.0;
    //j[2] = 3.1;
    std::pair<int, double> pa = std::make_pair(1, 10.1);
    j.push_back(pa);
    j.push_back(pa);
    j.push_back(pa);
    
    cout<<j.dump()<<endl;
    cout<<j.size()<<endl;

    json jj = json::parse(j.dump());

    // cout << jj.size() <<endl;
    vector<pair<int, double> > pa_res = jj.get<vector<pair<int, double> > >();
    
    cout << pa_res.size() <<endl;
    for (int i = 0; i < jj.size(); ++i){
       cout<<pa_res[i].first<<" "<<pa_res[i].second<<" "<<endl;
    }

}
