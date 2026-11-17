import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { HhmmPipe, PctPipe, VnNumberPipe } from '../../core/format';
import { EventSummary, HANDLING_TEXT, Overview, STATUS_TEXT } from '../../core/models';
import { LabelStore } from '../../shared/bins';

@Component({
  selector: 'app-overview',
  imports: [RouterLink, HhmmPipe, PctPipe, VnNumberPipe],
  templateUrl: './overview.html',
  styleUrl: './overview.scss',
})
export class OverviewPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly store = inject(LabelStore);

  protected readonly overview = signal<Overview | null>(null);
  protected readonly events = signal<EventSummary[]>([]);
  protected readonly loading = signal(true);
  protected readonly simulating = signal(false);

  protected readonly simulated = computed(
    () => !!this.overview()?.simulated || this.events().some((e) => e.simulated),
  );
  protected readonly maxMislabel = computed(() =>
    Math.max(1, ...(this.overview()?.top_mislabels ?? []).map((m) => m.count)),
  );
  protected readonly statusText = STATUS_TEXT;
  protected readonly handlingText = HANDLING_TEXT;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    forkJoin({ ov: this.api.overview(), ev: this.api.events({ limit: 8 }) }).subscribe({
      next: ({ ov, ev }) => {
        this.overview.set(ov);
        this.events.set(ev);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  simulate(): void {
    this.simulating.set(true);
    this.api.simulate(12).subscribe({
      next: () => {
        this.simulating.set(false);
        this.load();
      },
      error: () => this.simulating.set(false),
    });
  }
}
