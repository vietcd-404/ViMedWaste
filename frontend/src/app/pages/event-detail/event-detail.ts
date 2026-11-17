import { Component, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { DateTimePipe, HhmmPipe, VnNumberPipe } from '../../core/format';
import { EventDetail, HANDLING_TEXT, Handling, Verdict } from '../../core/models';
import { LabelStore } from '../../shared/bins';
import { LabelBars } from '../../shared/label-bars';
import { StatusBadge } from '../../shared/status-badge';

@Component({
  selector: 'app-event-detail',
  imports: [RouterLink, DateTimePipe, HhmmPipe, VnNumberPipe, LabelBars, StatusBadge],
  templateUrl: './event-detail.html',
  styleUrl: './event-detail.scss',
})
export class EventDetailPage {
  /** Tham số :id của route (withComponentInputBinding). */
  readonly id = input.required<string>();

  private readonly api = inject(ApiService);
  protected readonly store = inject(LabelStore);
  protected readonly event = signal<EventDetail | null>(null);
  protected readonly showCam = signal(true);
  protected readonly busy = signal(false);
  protected readonly notFound = signal(false);
  protected readonly handlingText = HANDLING_TEXT;
  protected readonly handlings: Handling[] = ['CHUA_XU_LY', 'DA_LAY_RA', 'CHO_XEM_LAI'];

  constructor() {
    effect(() => {
      const id = Number(this.id());
      this.notFound.set(false);
      this.api.event(id).subscribe({
        next: (e) => this.event.set(e),
        error: () => this.notFound.set(true),
      });
    });
  }

  protected afterSrc(e: EventDetail): string {
    return this.showCam() && e.images.gradcam ? e.images.gradcam : e.images.after;
  }

  protected binColor(e: EventDetail): string {
    return this.store.bin(e.bin_type)?.color ?? '#9CA3AF';
  }

  protected binBorder(e: EventDetail): string {
    return this.store.bin(e.bin_type)?.border ?? '#6B7280';
  }

  protected sendFeedback(verdict: Verdict): void {
    const e = this.event();
    if (!e) return;
    this.busy.set(true);
    this.api.feedback(e.id, verdict).subscribe({
      next: (r) => { this.event.set(r); this.busy.set(false); },
      error: () => this.busy.set(false),
    });
  }

  protected setHandling(h: string): void {
    const e = this.event();
    if (!e) return;
    this.api.handling(e.id, h as Handling).subscribe({ next: (r) => this.event.set(r), error: () => {} });
  }
}
