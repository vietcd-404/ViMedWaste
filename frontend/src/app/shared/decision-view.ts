import { Component, computed, inject, input } from '@angular/core';
import { Decision } from '../core/models';
import { VnNumberPipe } from '../core/format';
import { LabelBars } from './label-bars';
import { LabelStore } from './bins';

/** Kết quả một lần nhận dạng: banner trạng thái, vi phạm, 10 nhãn, điểm lớp mở. */
@Component({
  selector: 'app-decision-view',
  imports: [LabelBars, VnNumberPipe],
  template: `
    @let d = decision();
    <section class="banner" [class]="'banner ' + tone()" role="status">
      <div class="banner-title">{{ heading() }}</div>
      <div class="banner-text">{{ d.title }}</div>
    </section>

    @if (d.violations.length) {
      <div class="violations">
        @for (code of d.violations; track code) {
          @let l = labelOf(code);
          @if (l) {
            <div class="vio">
              <span><b>{{ l.code }}</b> · {{ l.name }}</span>
              <span class="to">→ bỏ vào
                @for (b of l.correct_bins; track b; let last = $last) {
                  <span class="bin"><span class="bin-chip" [style.background]="store.bin(b)?.color" [style.border-color]="store.bin(b)?.border"></span> {{ b }}</span>@if (!last) {<span>, </span>}
                }
              </span>
            </div>
          }
        }
      </div>
    }

    @if (d.ood_score !== null && d.tau !== null) {
      <p class="note">
        Điểm quen thuộc S(x) = {{ d.ood_score | vn: 2 }}
        {{ d.accepted ? '≥' : '<' }} ngưỡng τ = {{ d.tau | vn: 2 }},
        {{ d.accepted ? 'nên hệ thống được phép kết luận.' : 'nên hệ thống không đưa ra nhãn.' }}
      </p>
    }

    <app-label-bars [labels]="d.labels" />

    @if (d.model.warning) {
      <p class="model-warn">{{ d.model.warning }}</p>
    }
  `,
  styles: `
    :host { display: flex; flex-direction: column; gap: 16px; }
    .banner { border-radius: 14px; padding: 16px 20px; border: 2px solid; }
    .banner-title { font-size: 20px; font-weight: 700; }
    .banner-text { font-size: 15px; margin-top: 2px; }
    .banner.warn { background: var(--warn-soft); border-color: var(--warn); color: var(--warn-ink); }
    .banner.ok { background: var(--teal-soft); border-color: var(--teal); color: var(--teal); }
    .banner.unknown { background: var(--grey-soft); border-color: var(--grey); color: var(--grey); }
    .violations { display: flex; flex-direction: column; gap: 8px; }
    .vio {
      display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
      background: #FFF7F1; border: 1px solid #F1C9A8; border-radius: 10px; padding: 10px 14px;
    }
    .to { color: var(--muted); }
    .bin { white-space: nowrap; color: var(--ink); font-weight: 600; }
    .model-warn { font-size: 13px; color: var(--warn-ink); background: #FFF7F1; border-radius: 10px; padding: 10px 12px; }
  `,
})
export class DecisionView {
  readonly decision = input.required<Decision>();
  protected readonly store = inject(LabelStore);

  protected readonly tone = computed(() =>
    ({ CANH_BAO: 'warn', PHU_HOP: 'ok', KHONG_XAC_DINH: 'unknown' } as const)[this.decision().status],
  );
  protected readonly heading = computed(() =>
    ({
      CANH_BAO: 'CẢNH BÁO: bỏ sai thùng',
      PHU_HOP: 'PHÙ HỢP',
      KHONG_XAC_DINH: 'KHÔNG XÁC ĐỊNH',
    } as const)[this.decision().status],
  );

  protected labelOf(code: string) {
    return this.decision().labels.find((l) => l.code === code);
  }
}
