import { Injectable, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, of } from 'rxjs';
import { ApiService } from '../core/api.service';
import { Bin, LabelsResponse } from '../core/models';

/** Bảng nhãn và màu thùng lấy một lần từ /api/labels, dùng chung cho mọi trang. */
@Injectable({ providedIn: 'root' })
export class LabelStore {
  private readonly api = inject(ApiService);
  readonly data = toSignal(this.api.labels().pipe(catchError(() => of(null as LabelsResponse | null))), {
    initialValue: null,
  });
  readonly bins = computed(() => this.data()?.bins ?? []);
  readonly labels = computed(() => this.data()?.labels ?? []);
  private readonly binMap = computed(() => new Map(this.bins().map((b) => [b.code, b])));

  bin(code: string | null | undefined): Bin | undefined {
    return code ? this.binMap().get(code) : undefined;
  }

  /** "B4 · Xanh, thông thường" */
  binText(code: string | null | undefined): string {
    const b = this.bin(code);
    return b ? `${b.code} · ${b.short || b.name}` : (code ?? '');
  }
}
