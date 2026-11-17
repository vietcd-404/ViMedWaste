import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, shareReplay, tap, throwError } from 'rxjs';
import {
  Decision, EventDetail, EventSummary, Handling, LabelsResponse, ModelInfo, Overview,
  Settings, Station, Verdict, Zone,
} from './models';

/** Gọi BE FastAPI qua proxy /api (docs/API.md). */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  /** Lỗi gần nhất, hiển thị thân thiện ở khung ứng dụng. */
  readonly lastError = signal<string | null>(null);

  private labels$?: Observable<LabelsResponse>;

  health() {
    return this.wrap(this.http.get<{ status: string; model_available: boolean }>(`${this.base}/health`));
  }

  /** Bảng nhãn ít thay đổi: lưu lại cho cả phiên. */
  labels(): Observable<LabelsResponse> {
    this.labels$ ??= this.wrap(this.http.get<LabelsResponse>(`${this.base}/labels`)).pipe(shareReplay(1));
    return this.labels$;
  }

  model() {
    return this.wrap(this.http.get<ModelInfo>(`${this.base}/model`));
  }

  predict(image: File, binType: string) {
    const form = new FormData();
    form.append('image', image);
    form.append('bin_type', binType);
    return this.wrap(this.http.post<Decision>(`${this.base}/predict`, form));
  }

  stations() {
    return this.wrap(this.http.get<Station[]>(`${this.base}/stations`));
  }

  station(id: string) {
    return this.wrap(this.http.get<Station>(`${this.base}/stations/${id}`));
  }

  saveConfig(id: string, zones: Zone[], settings: Settings) {
    return this.wrap(this.http.put<Station>(`${this.base}/stations/${id}/config`, { zones, settings }));
  }

  snapshotUrl(id: string, bust = Date.now()) {
    return `${this.base}/stations/${id}/snapshot?t=${bust}`;
  }

  testCapture(id: string, zoneNo: number, image?: File) {
    const form = new FormData();
    form.append('zone_no', String(zoneNo));
    if (image) form.append('image', image);
    return this.wrap(this.http.post<Decision>(`${this.base}/stations/${id}/test-capture`, form));
  }

  events(filter: { status?: string; station_id?: string; limit?: number } = {}) {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(filter)) {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    }
    return this.wrap(this.http.get<EventSummary[]>(`${this.base}/events`, { params }));
  }

  event(id: number) {
    return this.wrap(this.http.get<EventDetail>(`${this.base}/events/${id}`));
  }

  feedback(id: number, verdict: Verdict, note?: string) {
    return this.wrap(this.http.post<EventDetail>(`${this.base}/events/${id}/feedback`, { verdict, note }));
  }

  handling(id: number, handling: Handling) {
    return this.wrap(this.http.post<EventDetail>(`${this.base}/events/${id}/handling`, { handling }));
  }

  overview(date?: string) {
    const params = date ? new HttpParams().set('date', date) : undefined;
    return this.wrap(this.http.get<Overview>(`${this.base}/stats/overview`, { params }));
  }

  simulate(n = 12) {
    return this.wrap(this.http.post<EventSummary[]>(`${this.base}/simulate`, { n }));
  }

  private wrap<T>(obs: Observable<T>): Observable<T> {
    return obs.pipe(
      tap(() => this.lastError.set(null)),
      catchError((err: HttpErrorResponse) => {
        this.lastError.set(friendlyError(err));
        return throwError(() => err);
      }),
    );
  }
}

export function friendlyError(err: HttpErrorResponse): string {
  if (err.status === 0 || err.status === 502 || err.status === 504) {
    return 'Không kết nối được máy chủ ViMedWaste. Kiểm tra backend đang chạy ở cổng 8000.';
  }
  const detail = typeof err.error === 'object' && err.error?.detail ? String(err.error.detail) : '';
  if (err.status === 404) return detail || 'Không tìm thấy dữ liệu yêu cầu.';
  if (err.status === 422) return detail || 'Dữ liệu gửi lên chưa hợp lệ.';
  return detail || `Máy chủ báo lỗi (${err.status}).`;
}
