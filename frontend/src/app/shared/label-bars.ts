import { Component, computed, input } from '@angular/core';
import { LabelScore } from '../core/models';
import { pct } from '../core/format';

/** Thanh xác suất từng nhãn, có vạch ngưỡng; nhãn vi phạm màu cam, đúng thùng màu teal. */
@Component({
  selector: 'app-label-bars',
  template: `
    @for (l of shown(); track l.code) {
      <div class="row" [class.violation]="l.violation" [class.ok]="l.present && !l.violation">
        <div class="head">
          <span class="name"><b>{{ l.code }}</b> · {{ l.name }}</span>
          <span class="verdict tnum">{{ verdict(l) }}</span>
        </div>
        <div class="track" role="img" [attr.aria-label]="l.name + ': ' + fmt(l.prob) + ', ngưỡng ' + fmt(l.threshold)">
          <div class="fill" [style.width.%]="l.prob * 100"></div>
          <div class="tick" [style.left.%]="l.threshold * 100"></div>
        </div>
      </div>
    } @empty {
      <p class="note">Mô hình không nhận ra nhãn nào vượt ngưỡng.</p>
    }
  `,
  styles: `
    :host { display: flex; flex-direction: column; gap: 16px; }
    .head { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; margin-bottom: 6px; }
    .name b { font-weight: 700; }
    .verdict { color: var(--muted); white-space: nowrap; }
    .track { position: relative; height: 14px; border-radius: 999px; background: #E9ECEB; }
    .fill { position: absolute; inset: 0 auto 0 0; border-radius: 999px; background: #9AA5B1; }
    .tick { position: absolute; top: -5px; bottom: -5px; width: 2px; background: var(--ink); }
    .violation .verdict { color: var(--warn-ink); font-weight: 600; }
    .violation .fill { background: var(--warn); }
    .violation .track { background: #F7E2D6; }
    .ok .verdict { color: var(--teal); font-weight: 600; }
    .ok .fill { background: var(--teal); }
  `,
})
export class LabelBars {
  readonly labels = input.required<LabelScore[]>();
  /** true: chỉ hiện nhãn có mặt; false: hiện đủ 10 nhãn. */
  readonly onlyPresent = input(false);

  protected readonly shown = computed(() =>
    this.onlyPresent() ? this.labels().filter((l) => l.present) : this.labels(),
  );

  protected fmt(v: number) {
    return pct(v);
  }

  protected verdict(l: LabelScore): string {
    if (l.violation) return `Sai thùng · ${pct(l.prob)}`;
    if (l.present) return `Đúng thùng · ${pct(l.prob)}`;
    return pct(l.prob);
  }
}
