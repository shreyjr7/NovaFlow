// src/pages/RoadDefects/types.ts
// Shared TypeScript types for Road Defect Management (Phase 18)

export type DefectClass =
  | "pothole"
  | "damaged_road"
  | "waterlogging"
  | "missing_road_divider"
  | "missing_zebra"
  | "damaged_sign"
  | "missing_sign"
  | "surface_erosion"
  | "missing_manhole";

export type DefectSeverity = "CRITICAL" | "SEVERE" | "HIGH" | "MEDIUM" | "LOW";

export type DefectLifecycleState =
  | "AI_DETECTED"
  | "UNVERIFIED"
  | "CONFIRMED"
  | "ASSIGNED"
  | "UNDER_REPAIR"
  | "RESOLVED"
  | "REOPENED_UNDER_REVIEW"
  | "REJECTED";

// Legacy alias
export type DefectStatus = DefectLifecycleState | "OPEN" | "IN_PROGRESS" | "FALSE_POSITIVE";

export interface DefectPriorityBreakdown {
  severity_score: number;
  traffic_volume_score: number;
  detections_score: number;
  location_importance_score: number;
  safety_risk_score: number;
  persistence_score: number;
  total_priority_score: number;
  priority_tier: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
}

export interface MaintenanceTicket {
  ticket_id: string;
  assigned_authority: string;
  assigned_contractor?: string;
  target_completion_date?: string;
  work_order_notes?: string;
  created_at: string;
  status: string;
}

export interface RepairEvidence {
  evidence_id: string;
  before_image_b64?: string;
  after_image_b64?: string;
  completion_notes: string;
  engineer_id: string;
  uploaded_at: string;
  completion_certificate_url?: string;
}

export interface AuditLogEntry {
  timestamp: string;
  actor: string;
  action: string;
  from_status: string;
  to_status: string;
  notes?: string;
}

export interface DefectEvent {
  defect_id: string;
  event_id: string;
  event_type: string;
  cls: DefectClass;
  type?: string;
  label?: string;
  confidence: number;
  severity: DefectSeverity;
  road_segment: string;
  bounding_box?: number[];
  camera_id: string;
  bus_id: string;
  timestamp: string;
  first_detected?: string;
  last_detected?: string;
  buses_confirming?: string[];
  number_of_buses_confirming?: number;
  detection_count?: number;
  assigned_authority?: string;
  maintenance_ticket?: MaintenanceTicket;
  priority_score?: number;
  priority_breakdown?: DefectPriorityBreakdown;
  repair_evidence?: RepairEvidence;
  closed_at?: string;
  closed_by?: string;
  reopened_at?: string;
  reopen_reason?: string;
  reopen_count?: number;
  audit_history?: AuditLogEntry[];
  gps: {
    lat: number;
    lon: number;
    bearing_deg?: number;
    address?: string;
    district?: string;
  };
  frame_b64?: string;
  status: DefectStatus;
  quality?: {
    status: string;
    blur_score: number;
    brightness: number;
  };
}

export interface DefectSummary {
  total: number;
  by_class: Record<string, number>;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
}
