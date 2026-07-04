export type UserRole = "admin" | "analyst" | "viewer";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface MetricsSummary {
  total_predictions: number;
  attack_predictions: number;
  benign_predictions: number;
  total_alerts: number;
  unacknowledged_alerts: number;
  avg_latency_ms: number;
  attack_rate: number;
  active_mitigations: number;
  flows_blocked: number;
  avg_time_to_mitigate_ms: number;
}

export interface Alert {
  id: number;
  victim_ip: string;
  severity: string;
  title: string;
  message: string;
  probability: number;
  acknowledged: boolean;
  created_at: string;
}

export interface PredictionHistory {
  id: number;
  victim_ip: string;
  model_name: string;
  is_attack: boolean;
  probability: number;
  latency_ms: number;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  models: { gcn: boolean; gat: boolean; rf: boolean };
}

export interface DemoStatus {
  simulator_enabled: boolean;
  simulator_running: boolean;
  traffic_windows: number;
  attack_windows?: number;
  benign_windows?: number;
  simulator_interval_seconds: number;
  models_loaded: boolean;
  models: { gcn: boolean; gat: boolean; rf: boolean };
}

export interface GraphNode {
  id: number;
  ip: string;
  is_victim: boolean;
  is_source: boolean;
  degree: number;
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
}

export interface LiveGraph {
  victim_ip: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_attack: boolean | null;
  probability: number | null;
  num_flows: number;
}

export interface PredictResponse {
  is_attack: boolean;
  probability: number;
  model: string;
  victim_ip: string;
  num_nodes: number;
  num_edges: number;
  num_flows: number;
  latency_ms: number;
  message: string;
}

export interface FlowRecord {
  source_ip: string;
  destination_ip: string;
  source_port?: number;
  destination_port?: number;
  protocol?: number;
  flow_duration?: number;
  total_fwd_packets?: number;
  total_backward_packets?: number;
  flow_bytes_s?: number;
  flow_packets_s?: number;
  syn_flag_count?: number;
  ack_flag_count?: number;
}

export interface MitigationRecord {
  id: number;
  source_ip: string;
  victim_ip: string;
  action: string;
  status: string;
  score: number;
  reason: string;
  rule_text: string | null;
  alert_id: number | null;
  prediction_id: number | null;
  auto_triggered: boolean;
  detection_to_action_ms: number;
  applied_at: string;
  revoked_at: string | null;
}

export interface MitigationSummary {
  active_blocks: number;
  active_rate_limits: number;
  active_quarantines: number;
  total_active: number;
  total_applied: number;
  total_revoked: number;
  avg_time_to_mitigate_ms: number;
  mode: string;
  auto_enabled: boolean;
}

export interface PreventionStats {
  flows_blocked: number;
  flows_allowed: number;
  mitigation_summary: MitigationSummary;
}
