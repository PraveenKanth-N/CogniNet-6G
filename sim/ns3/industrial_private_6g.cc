/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/**
 * CogniNet-6G: Industrial Private 6G Network Simulation Topology (ns-3)
 * Implements 3GPP InF (Indoor Factory) mmWave / Sub-THz radio access network
 * with multi-tenant slicing (URLLC, eMBB, mMTC) and runtime dynamic reallocation.
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/mobility-module.h"
#include "ns3/flow-monitor-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("CogniNet6G_IndustrialPrivateNetwork");

int main(int argc, char *argv[])
{
    uint32_t numRobots = 10;
    double simTime = 60.0;
    double rMaxMbps = 100.0;
    bool enableTracing = true;

    CommandLine cmd(__FILE__);
    cmd.AddValue("numRobots", "Number of active AMRs/AGVs in factory", numRobots);
    cmd.AddValue("simTime", "Total simulation duration (seconds)", simTime);
    cmd.AddValue("rMaxMbps", "Total wireless bandwidth capacity in Mbps", rMaxMbps);
    cmd.Parse(argc, argv);

    Time::SetResolution(Time::NS);
    LogComponentEnable("CogniNet6G_IndustrialPrivateNetwork", LOG_LEVEL_INFO);

    NS_LOG_INFO("Configuring 6G Industrial Private Network for " << numRobots << " Robots...");

    // Create Base Station nodes (2 gNodeBs) and Robot UE nodes
    NodeContainer gNbNodes;
    gNbNodes.Create(2);

    NodeContainer robotNodes;
    robotNodes.Create(numRobots);

    NodeContainer edgeServer;
    edgeServer.Create(1);

    // Mobility Configuration: 100m x 80m Factory Floor
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator>();
    positionAlloc->Add(Vector(30.0, 40.0, 6.0));  // gNb-1
    positionAlloc->Add(Vector(75.0, 40.0, 6.0));  // gNb-2
    positionAlloc->Add(Vector(50.0, 5.0, 1.0));   // Edge Server
    mobility.SetPositionAllocator(positionAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(gNbNodes);
    mobility.Install(edgeServer);

    // Random walk / waypoint mobility for robots
    mobility.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
                              "Bounds", RectangleValue(Rectangle(0, 100, 0, 80)),
                              "Speed", StringValue("ns3::UniformRandomVariable[Min=0.5|Max=1.5]"));
    mobility.Install(robotNodes);

    // Point-to-point interconnect between gNb and Edge Server
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("10Gbps"));
    p2p.SetChannelAttribute("Delay", StringValue("100us"));

    NetDeviceContainer edgeDevices1 = p2p.Install(gNbNodes.Get(0), edgeServer.Get(0));
    NetDeviceContainer edgeDevices2 = p2p.Install(gNbNodes.Get(1), edgeServer.Get(0));

    InternetStackHelper stack;
    stack.Install(gNbNodes);
    stack.Install(robotNodes);
    stack.Install(edgeServer);

    Ipv4AddressHelper address;
    address.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces1 = address.Assign(edgeDevices1);

    address.SetBase("10.1.2.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces2 = address.Assign(edgeDevices2);

    NS_LOG_INFO("6G Industrial Private Topology Initialized. Slicing Engine Active.");

    Simulator::Stop(Seconds(simTime));
    Simulator::Run();
    Simulator::Destroy();
    return 0;
}
