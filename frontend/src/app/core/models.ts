// Kiểu dữ liệu theo hợp đồng docs/API.md.

export type DecisionStatus = 'CANH_BAO' | 'PHU_HOP' | 'KHONG_XAC_DINH';
export type Handling = 'CHUA_XU_LY' | 'DA_LAY_RA' | 'CHO_XEM_LAI';
export type Verdict = 'DUNG' | 'NHAM';
export type Box = [number, number, number, number];

export interface Bin {
  code: string;
  name: string;
  short: string;
  color: string;
  border: string;
}

export interface LabelInfo {
  code: string;
  name: string;
  group: string;
  group_name: string;
  correct_bins: string[];
  c_fn: number;
  threshold: number;
  example: string;
}

export interface LabelsResponse {
  labels: LabelInfo[];
  bins: Bin[];
  compatibility: Record<string, string[]>;
}

export interface LabelScore {
  code: string;
  name: string;
  prob: number;
  threshold: number;
  present: boolean;
  violation: boolean;
  correct_bins: string[];
}

export interface ModelRef {
  available: boolean;
  trained_on: string | null;
  warning: string | null;
}

export interface Decision {
  status: DecisionStatus;
  bin_type: string;
  title: string;
  labels: LabelScore[];
  violations: string[];
  ood_score: number | null;
  tau: number | null;
  accepted: boolean;
  model: ModelRef;
  gradcam?: string | null;
}

export interface Zone {
  zone_no: number;
  bin_type: string;
  box: Box;
}

export interface Settings {
  still_seconds: number;
  motion_sensitivity: number;
  buzzer_volume: number;
  dry_run: boolean;
}

export interface Station {
  id: string;
  name: string;
  location: string;
  online: boolean;
  last_seen: string | null;
  zones: Zone[];
  settings: Settings;
}

export interface EventSummary {
  id: number;
  time: string;
  station_id: string;
  station_name: string;
  zone_no: number;
  bin_type: string;
  status: DecisionStatus;
  title: string;
  handling: Handling | null;
  feedback: Verdict | null;
  simulated: boolean;
}

export interface EventDetail extends EventSummary {
  decision: Decision;
  images: { before: string | null; after: string; gradcam: string | null };
  change_box: Box | null;
  timeline: { time: string; text: string }[];
}

export interface Overview {
  date: string;
  total: number;
  warnings: number;
  handled_pct: number;
  unknown: number;
  top_mislabels: { code: string; name: string; count: number }[];
  stations: { id: string; name: string; online: boolean }[];
  simulated: boolean;
}

export interface ModelInfo {
  available: boolean;
  backbone?: string;
  trained_on?: string;
  trained_labels?: string[];
  warning?: string;
  temperature?: number;
  tau?: number;
  [key: string]: unknown;
}

export const STATUS_TEXT: Record<DecisionStatus, string> = {
  CANH_BAO: 'Cảnh báo',
  PHU_HOP: 'Phù hợp',
  KHONG_XAC_DINH: 'Không xác định',
};

export const HANDLING_TEXT: Record<Handling, string> = {
  CHUA_XU_LY: 'Chưa xử lý',
  DA_LAY_RA: 'Đã lấy ra',
  CHO_XEM_LAI: 'Chờ xem lại',
};
