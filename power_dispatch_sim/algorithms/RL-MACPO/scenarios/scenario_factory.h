#ifndef SCENARIO_FACTORY_H
#define SCENARIO_FACTORY_H

#include <cstdlib>
#include <iostream>
#include <string>
#include "./power_grid/PowerGridBenchmarks.h"
#include "./resource_alloc/ResourceAllocBenchmarks.h"
#include "./ev_dispatch/EvDispatchBenchmarks.h"
#include "./maed/MaedSingleAreaBenchmarks.h"
#include "./maed/MaedMultiAreaBenchmarks.h"

/** 附录 V/VI 配对实验统一协议（MACPO 与 RL-MACPO 必须一致） */
struct PairedProtocol {
    double gen_per_d = 3.0;
    int eva_per_d = 20000;
    int swarm_size = 100;
    double dynamic_weight = 512.0;  // λ=1/512, w=|f|/512
};

inline PairedProtocol paired_protocol() { return PairedProtocol{}; }

struct ScenarioConfig {
    std::string id;
    std::string label;
    int required_ranks = 0;
    double gen_per_d = 2.0;
    int eva_per_d = 5000;
    int swarm_size = 100;
    double dynamic_weight = 512.0;
};

inline ScenarioConfig scenario_config(const std::string& name) {
    PairedProtocol proto = paired_protocol();
    ScenarioConfig c;
    if (name == "RESOURCE" || name == "RA") {
        c.id = "RESOURCE";
        c.label = "Appendix-V Resource Allocation";
        c.required_ranks = RA_NUM_NODES;
        c.gen_per_d = proto.gen_per_d;
        c.eva_per_d = proto.eva_per_d;
        c.swarm_size = proto.swarm_size;
        c.dynamic_weight = proto.dynamic_weight;
    } else if (name == "EVDISPATCH" || name == "EV") {
        c.id = "EVDISPATCH";
        c.label = "Appendix-VI EV Electric Dispatch";
        c.required_ranks = EV_NUM_NODES;
        c.gen_per_d = proto.gen_per_d;
        c.eva_per_d = proto.eva_per_d;
        c.swarm_size = proto.swarm_size;
        c.dynamic_weight = proto.dynamic_weight;
    } else if (name == "POWER14" || name == "IEEE14") {
        c.id = "POWER14";
        c.label = "IEEE 14-bus Economic Dispatch";
        c.required_ranks = 4;
        c.gen_per_d = 2.0;
        c.eva_per_d = 4000;
        c.swarm_size = 100;
    } else if (name == "POWER30" || name == "IEEE30") {
        c.id = "POWER30";
        c.label = "IEEE 30-bus Economic Dispatch";
        c.required_ranks = 4;
        c.gen_per_d = 2.0;
        c.eva_per_d = 4000;
        c.swarm_size = 100;
    } else if (name == "POWER57" || name == "IEEE57") {
        c.id = "POWER57";
        c.label = "IEEE 57-bus Economic Dispatch";
        c.required_ranks = 4;
        c.gen_per_d = 2.0;
        c.eva_per_d = 4000;
        c.swarm_size = 100;
    } else if (name == "POWER118" || name == "IEEE118") {
        c.id = "POWER118";
        c.label = "IEEE 118-bus Economic Dispatch";
        c.required_ranks = 8;
        c.gen_per_d = 2.0;
        c.eva_per_d = 4000;
        c.swarm_size = 100;
    } else if (name == "MAED13" || name == "VPE13") {
        c.id = "MAED13";
        c.label = "13-Unit VPE Economic Dispatch (single area)";
        c.required_ranks = 1;
        c.gen_per_d = 4.0;
        c.eva_per_d = 25000;
        c.swarm_size = 100;
        c.dynamic_weight = 512.0;
    } else if (name == "MAED2" || name == "MAED2AREA") {
        c.id = "MAED2";
        c.label = "2-Area MAED (13 units + tie line)";
        c.required_ranks = 2;
        c.gen_per_d = 3.0;
        c.eva_per_d = 20000;
        c.swarm_size = 100;
        c.dynamic_weight = 512.0;
    } else {
        c.id = "UNKNOWN";
    }
    return c;
}

inline Benchmarks* create_scenario_benchmark(const std::string& name) {
    if (name == "RESOURCE" || name == "RA")
        return new ResourceAllocBenchmarks();
    if (name == "EVDISPATCH" || name == "EV")
        return new EvDispatchBenchmarks();
    if (name == "POWER14" || name == "IEEE14")
        return new PowerGridBenchmarks(IeeeGridCaseId::IEEE14);
    if (name == "POWER30" || name == "IEEE30")
        return new PowerGridBenchmarks(IeeeGridCaseId::IEEE30);
    if (name == "POWER57" || name == "IEEE57")
        return new PowerGridBenchmarks(IeeeGridCaseId::IEEE57);
    if (name == "POWER118" || name == "IEEE118")
        return new PowerGridBenchmarks(IeeeGridCaseId::IEEE118);
    if (name == "MAED13" || name == "VPE13")
        return new MaedSingleAreaBenchmarks();
    if (name == "MAED2" || name == "MAED2AREA")
        return new MaedMultiAreaBenchmarks();
    return nullptr;
}

#endif
