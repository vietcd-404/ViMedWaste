import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { DateTimePipe } from '../../core/format';
import { EventSummary, HANDLING_TEXT, Station } from '../../core/models';
import { StatusBadge } from '../../shared/status-badge';

@Component({
  selector: 'app-events',
  imports: [FormsModule, RouterLink, DateTimePipe, StatusBadge],
  template: `
    <div class="page">
      <div class="page-head"><h1>Sự kiện</h1></div>
      <div class="filters">
        <label>Trạng thái
          <select class="field" [(ngModel)]="status" (ngModelChange)="load()">
            <option value="">Tất cả</option>
            <option value="CANH_BAO">Cảnh báo</option>
            <option value="PHU_HOP">Phù hợp</option>
            <option value="KHONG_XAC_DINH">Không xác định</option>
          </select>
        </label>
        <label>Trạm
          <select class="field" [(ngModel)]="stationId" (ngModelChange)="load()">
            <option value="">Tất cả</option>
            @for (s of stations(); track s.id) { <option [value]="s.id">{{ s.name }}</option> }
          </select>
        </label>
      </div>

      <section class="card">
        @if (events().length) {
          <div class="table-wrap">
            <table class="tbl">
              <thead><tr><th>Thời gian</th><th>Trạm · Vùng</th><th>Kết quả</th><th>Trạng thái</th><th>Xử lý</th><th></th></tr></thead>
              <tbody>
                @for (e of events(); track e.id) {
                  <tr>
                    <td class="tnum">{{ e.time | dateTime }}</td>
                    <td>{{ e.station_name }} · Vùng {{ e.zone_no }} ({{ e.bin_type }})</td>
                    <td><a [routerLink]="['/su-kien', e.id]" [class.warn-text]="e.status === 'CANH_BAO'">{{ e.title }}</a></td>
                    <td><app-status-badge [status]="e.status" /></td>
                    <td>{{ e.handling ? handlingText[e.handling] : '–' }}</td>
                    <td>@if (e.simulated) { <span class="badge sim">Mô phỏng</span> }</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else if (!loading()) {
          <div class="empty">Không có sự kiện phù hợp bộ lọc.</div>
        }
      </section>
    </div>
  `,
  styles: `
    .filters { display: flex; gap: 16px; flex-wrap: wrap; }
    .filters label { display: flex; align-items: center; gap: 10px; color: var(--muted); }
    .table-wrap { overflow-x: auto; }
    td a { color: var(--ink-2); }
    td a.warn-text { color: var(--warn-ink); }
  `,
})
export class EventsPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly events = signal<EventSummary[]>([]);
  protected readonly stations = signal<Station[]>([]);
  protected readonly loading = signal(true);
  protected readonly handlingText = HANDLING_TEXT;
  protected status = '';
  protected stationId = '';

  ngOnInit(): void {
    this.api.stations().subscribe({ next: (s) => this.stations.set(s), error: () => {} });
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.events({ status: this.status, station_id: this.stationId, limit: 100 }).subscribe({
      next: (e) => {
        this.events.set(e);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
