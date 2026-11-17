import { Component, computed, input } from '@angular/core';
import { DecisionStatus, STATUS_TEXT } from '../core/models';

@Component({
  selector: 'app-status-badge',
  template: `<span class="badge" [class]="cls()">{{ text() }}</span>`,
})
export class StatusBadge {
  readonly status = input.required<DecisionStatus>();
  protected readonly text = computed(() => STATUS_TEXT[this.status()]);
  protected readonly cls = computed(() =>
    'badge ' + ({ CANH_BAO: 'warn', PHU_HOP: 'ok', KHONG_XAC_DINH: 'unknown' } as const)[this.status()],
  );
}
