"""
Monitoring & Telemetry Metrics Exporter
Converts CogniNet-6G runtime telemetry and closed-loop decision records
into InfluxDB Line Protocol and Prometheus exposition format for real-time observability.
"""

from typing import Dict, List, Any

class MetricsExporter:
    """
    Module for exporting telemetry and control loop telemetry to external TSDBs.
    Supports Prometheus format and InfluxDB Line Protocol.
    """
    def __init__(self, prefix: str = "cogninet"):
        self.prefix = prefix

    def to_influxdb_line(self, record: Dict[str, Any]) -> str:
        """
        Converts step record into InfluxDB Line Protocol format.
        Format: measurement[,tag_key=tag_val...] field_key=field_val[,field_key=field_val...] [timestamp]
        """
        timestamp_ns = int(record.get("timestamp", 0.0) * 1e9)
        lines = []

        # System state metrics
        state = record.get("state", [0.0, 0.0, 0.0, 0.0])
        timing = record.get("timing_ms", {})

        fields = [
            f"latency_ms={state[0]:.4f}",
            f"jitter_ms={state[1]:.4f}",
            f"packet_loss_ratio={state[2]:.6f}",
            f"channel_utilization={state[3]:.4f}",
            f"reward={record.get('reward', 0.0):.4f}",
            f"sla_violations={record.get('sla_violations', 0)}i",
            f"safety_override_applied={1 if record.get('safety_override_applied') else 0}i",
            f"reconfig_cost={record.get('reconfig_cost', 0.0):.6f}",
            f"total_loop_ms={timing.get('total_loop_ms', 0.0):.4f}",
            f"decision_ms={timing.get('decision_ms', 0.0):.4f}"
        ]
        line = f"{self.prefix}_system_metrics {','.join(fields)} {timestamp_ns}"
        lines.append(line)

        # Per-robot allocation and weight metrics
        allocs = record.get("allocations", {})
        weights = record.get("weights", {})
        for rid in allocs.keys():
            bw = allocs.get(rid, 0.0)
            w = weights.get(rid, 0.0)
            r_line = f"{self.prefix}_robot_metrics,robot_id={rid} bandwidth_mbps={bw:.4f},semantic_weight={w:.4f} {timestamp_ns}"
            lines.append(r_line)

        return "\n".join(lines)

    def to_prometheus_text(self, record: Dict[str, Any]) -> str:
        """
        Converts step record into Prometheus text exposition format.
        """
        state = record.get("state", [0.0, 0.0, 0.0, 0.0])
        lines = [
            f"# HELP {self.prefix}_latency_ms Mean 6G network latency in milliseconds",
            f"# TYPE {self.prefix}_latency_ms gauge",
            f"{self.prefix}_latency_ms {state[0]:.4f}",
            f"# HELP {self.prefix}_packet_loss_ratio Packet loss ratio",
            f"# TYPE {self.prefix}_packet_loss_ratio gauge",
            f"{self.prefix}_packet_loss_ratio {state[2]:.6f}",
            f"# HELP {self.prefix}_reward Step reward from Algorithm 1",
            f"# TYPE {self.prefix}_reward gauge",
            f"{self.prefix}_reward {record.get('reward', 0.0):.4f}",
        ]
        allocs = record.get("allocations", {})
        lines.append(f"# HELP {self.prefix}_bandwidth_mbps Per-slice bandwidth allocation")
        lines.append(f"# TYPE {self.prefix}_bandwidth_mbps gauge")
        for rid, bw in allocs.items():
            lines.append(f'{self.prefix}_bandwidth_mbps{{robot_id="{rid}"}} {bw:.4f}')

        return "\n".join(lines)
