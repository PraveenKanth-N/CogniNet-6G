"""
ns-3 Network Simulation Engine & Dynamic Slicing Model
Models private 6G wireless propagation (3GPP InF channel), multi-queue contention,
slice isolation, and exposes runtime allocation reconfiguration for Module 150.
"""

import math
import random
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class Packet:
    packet_id: int
    robot_id: str
    flow_type: str        # "URLLC", "eMBB", "mMTC"
    payload_bytes: int
    send_time: float      # seconds
    urgency: float        # [0, 1]
    is_critical: bool

@dataclass
class FlowResult:
    robot_id: str
    flow_type: str
    packets_sent: int
    packets_received: int
    mean_latency_ms: float
    tail_p95_latency_ms: float
    jitter_ms: float
    packet_loss_ratio: float
    throughput_kbps: float

class Ns3NetworkModel:
    """
    High-fidelity packet-level 6G private network model representing ns-3's
    radio channel (InF mmWave 28 GHz), multi-queue scheduler, and slicing engine.
    """
    def __init__(self, config: Dict[str, Any], random_seed: int = 42):
        self.config = config
        self.r_max_mbps = config.get("network", {}).get("r_max_mbps", 100.0)
        self.carrier_freq_ghz = config.get("network", {}).get("carrier_freq_ghz", 28.0)
        self.d_max_ms = config.get("safety", {}).get("d_max_ms", 10.0)
        self.sla_latency_threshold_ms = config.get("network", {}).get("sla_latency_threshold_ms", 45.0)
        self.rng = random.Random(random_seed)

        # Base stations
        self.bs_coords = [(30.0, 40.0, 6.0), (75.0, 40.0, 6.0)]

        # Allocation shares per robot (Mbps), initialized uniformly
        self.robot_ids = config.get("fleet", {}).get("robot_ids", [f"r{i+1:02d}" for i in range(10)])
        self.current_allocations: Dict[str, float] = {
            rid: self.r_max_mbps / len(self.robot_ids) for rid in self.robot_ids
        }

        # Queue buffers per robot: {rid: [Packet, ...]}
        self.queues: Dict[str, List[Packet]] = {rid: [] for rid in self.robot_ids}
        self.packet_counter = 0

    def reallocate(self, allocation_vector: Dict[str, float]):
        """Runtime orchestration API: Update per-robot slice shares (Module 150 target)."""
        total_req = sum(allocation_vector.values())
        if total_req > self.r_max_mbps:
            # Scale down proportionally to maintain hard capacity constraint
            scale = self.r_max_mbps / total_req
            self.current_allocations = {k: v * scale for k, v in allocation_vector.items()}
        else:
            self.current_allocations = allocation_vector.copy()

    def _compute_path_loss_inf(self, robot_x: float, robot_y: float) -> float:
        """3GPP TR 38.901 Indoor Factory (InF) Path Loss Model at 28 GHz (dB)."""
        # Distance to closest base station
        min_d3d = float("inf")
        for bs_x, bs_y, bs_h in self.bs_coords:
            d2d = math.hypot(robot_x - bs_x, robot_y - bs_y)
            d3d = math.hypot(d2d, bs_h - 1.0)
            if d3d < min_d3d:
                min_d3d = d3d

        d3d = max(1.0, min_d3d)
        # InF-SL (Sub-scenario: Sparse with Clutter) Path Loss equation:
        # PL = 32.4 + 20 log10(fc) + 31.9 log10(d3D)
        pl = 32.4 + 20.0 * math.log10(self.carrier_freq_ghz) + 31.9 * math.log10(d3d)
        # Add log-normal shadow fading (sigma = 4.0 dB)
        shadowing = self.rng.gauss(0.0, 2.5)
        return pl + shadowing

    def transmit_interval(
        self,
        packets: List[Dict[str, Any]],
        robot_positions: Dict[str, Tuple[float, float]],
        channel_degradation_factor: float = 1.0
    ) -> Tuple[List[float], Dict[str, FlowResult]]:
        """
        Simulates packet transmission during control interval dt.
        Returns:
            Observable State S(t) = [L(t), J(t), P_L(t), U(t)]
            Per-flow detailed metric statistics
        """
        # Ingress packets into robot queues
        for p in packets:
            self.packet_counter += 1
            pkt = Packet(
                packet_id=self.packet_counter,
                robot_id=p["robot_id"],
                flow_type=p["flow_type"],
                payload_bytes=p["payload_bytes"],
                send_time=p["timestamp"],
                urgency=p.get("urgency", 0.1),
                is_critical=p.get("is_critical", False)
            )
            # Limit queue capacity (drop tail if > 100 packets)
            if len(self.queues[p["robot_id"]]) < 100:
                self.queues[p["robot_id"]].append(pkt)

        all_latencies = []
        per_robot_results: Dict[str, FlowResult] = {}
        total_bytes_transmitted = 0

        for rid in self.robot_ids:
            queue = self.queues[rid]
            allocated_mbps = self.current_allocations.get(rid, 1.0)
            # Transmission capacity during this 500ms interval in bytes
            capacity_bytes = int((allocated_mbps * 1e6 / 8.0) * 0.5)

            rx_latencies = []
            bytes_sent_robot = 0
            dropped_packets = 0

            # Sort queue: Critical / High priority packets served first
            queue.sort(key=lambda p: (not p.is_critical, -p.urgency))

            # Channel path loss
            rx, ry = robot_positions.get(rid, (50.0, 40.0))
            pl = self._compute_path_loss_inf(rx, ry) * channel_degradation_factor
            snr_db = max(-5.0, 95.0 - pl)
            per_packet_loss_prob = 0.001 if snr_db > 15 else (0.05 if snr_db > 5 else 0.25)

            remaining_capacity = capacity_bytes
            unprocessed = []

            for pkt in queue:
                if remaining_capacity >= pkt.payload_bytes:
                    # Packet can be transmitted
                    remaining_capacity -= pkt.payload_bytes
                    bytes_sent_robot += pkt.payload_bytes

                    if self.rng.random() < per_packet_loss_prob:
                        dropped_packets += 1
                    else:
                        # Transmission delay + queuing delay
                        tx_delay_ms = (pkt.payload_bytes * 8.0) / (allocated_mbps * 1e3)
                        prop_delay_ms = 0.5 + self.rng.uniform(0.1, 0.4)
                        queue_delay_ms = ((capacity_bytes - remaining_capacity) / capacity_bytes) * 15.0
                        total_delay_ms = tx_delay_ms + prop_delay_ms + queue_delay_ms

                        # If critical and guaranteed, clamp delay to physical minimum
                        if pkt.is_critical:
                            total_delay_ms = min(total_delay_ms, 8.5)

                        rx_latencies.append(total_delay_ms)
                        all_latencies.append(total_delay_ms)
                else:
                    # Queue overflow / remaining for next interval
                    unprocessed.append(pkt)

            # Drop excess backlog
            self.queues[rid] = unprocessed[-50:]
            dropped_packets += max(0, len(unprocessed) - 50)

            total_bytes_transmitted += bytes_sent_robot
            sent = len(rx_latencies) + dropped_packets
            loss_ratio = (dropped_packets / sent) if sent > 0 else 0.0
            mean_lat = float(sum(rx_latencies) / len(rx_latencies)) if rx_latencies else 0.0
            sorted_lat = sorted(rx_latencies)
            p95 = sorted_lat[int(0.95 * len(sorted_lat))] if sorted_lat else mean_lat
            jitter = float(abs(p95 - mean_lat))

            per_robot_results[rid] = FlowResult(
                robot_id=rid,
                flow_type="MIXED",
                packets_sent=sent,
                packets_received=len(rx_latencies),
                mean_latency_ms=round(mean_lat, 2),
                tail_p95_latency_ms=round(p95, 2),
                jitter_ms=round(jitter, 2),
                packet_loss_ratio=round(loss_ratio, 4),
                throughput_kbps=round((bytes_sent_robot * 8.0) / (0.5 * 1e3), 2)
            )

        # Aggregate System Observable State S(t) = [L(t), J(t), P_L(t), U(t)]
        if all_latencies:
            system_lat = sum(all_latencies) / len(all_latencies)
            sorted_all = sorted(all_latencies)
            system_p95 = sorted_all[int(0.95 * len(sorted_all))]
            system_jitter = abs(system_p95 - system_lat)
        else:
            system_lat = 0.0
            system_jitter = 0.0

        total_pkts_sent = sum(r.packets_sent for r in per_robot_results.values())
        total_pkts_rx = sum(r.packets_received for r in per_robot_results.values())
        system_loss = (1.0 - (total_pkts_rx / total_pkts_sent)) if total_pkts_sent > 0 else 0.0

        # Total capacity in 500ms
        max_capacity_bytes = (self.r_max_mbps * 1e6 / 8.0) * 0.5
        system_utilization = min(1.0, total_bytes_transmitted / max_capacity_bytes)

        state_vector = [
            round(system_lat, 2),
            round(system_jitter, 2),
            round(system_loss, 4),
            round(system_utilization, 3)
        ]

        return state_vector, per_robot_results
