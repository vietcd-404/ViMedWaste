import { Component, OnDestroy, inject, signal } from '@angular/core';
import { ApiService } from '../../core/api.service';
import { Decision } from '../../core/models';
import { LabelStore } from '../../shared/bins';
import { DecisionView } from '../../shared/decision-view';

@Component({
  selector: 'app-check',
  imports: [DecisionView],
  template: `
    <div class="page">
      <div class="page-head"><h1>Kiểm tra thùng</h1></div>
      <p class="page-sub">Tải ảnh miệng thùng, chọn loại thùng, hệ thống cho biết có vật nào bỏ sai không.</p>

      <div class="grid-2 chk">
        <section class="card">
          <h2>1. Ảnh miệng thùng</h2>
          <label class="drop" [class.over]="dragOver()"
            (dragover)="$event.preventDefault(); dragOver.set(true)" (dragleave)="dragOver.set(false)"
            (drop)="onDrop($event)">
            <input type="file" accept="image/*" (change)="onPick($event)" />
            @if (preview(); as src) {
              <img [src]="src" alt="Ảnh đã chọn" />
            } @else {
              <span class="drop-text"><b>Kéo thả ảnh vào đây</b><br />hoặc bấm để chọn ảnh từ máy</span>
            }
          </label>
          @if (file(); as f) { <p class="note">{{ f.name }}</p> }

          <h2>2. Loại thùng</h2>
          <div class="bins" role="radiogroup" aria-label="Loại thùng">
            @for (b of store.bins(); track b.code) {
              <button type="button" class="bin" role="radio" [attr.aria-checked]="bin() === b.code"
                [class.on]="bin() === b.code" (click)="bin.set(b.code)">
                <span class="bin-chip" [style.background]="b.color" [style.border-color]="b.border"></span>
                <span><b>{{ b.code }}</b> · {{ b.short || b.name }}</span>
              </button>
            }
          </div>

          <button type="button" class="btn primary run" [disabled]="!file() || running()" (click)="run()">
            {{ running() ? 'Đang nhận dạng…' : 'Kiểm tra' }}
          </button>
        </section>

        <section class="card">
          <h2>Kết quả</h2>
          @if (result(); as d) {
            <app-decision-view [decision]="d" />
            @if (d.gradcam) {
              <figure>
                <img class="cam" [src]="d.gradcam" alt="Bản đồ Grad-CAM: vùng mô hình dựa vào để kết luận" />
                <figcaption class="note">Grad-CAM: vùng đỏ là nơi mô hình dựa vào để kết luận.</figcaption>
              </figure>
            }
          } @else {
            <div class="empty">Chưa có kết quả. Chọn ảnh và loại thùng rồi bấm "Kiểm tra".</div>
          }
        </section>
      </div>
    </div>
  `,
  styles: `
    .chk { grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); }
    .drop {
      position: relative; display: grid; place-items: center; min-height: 260px; border-radius: 14px;
      border: 2px dashed var(--line-strong); background: #F8FAF9; cursor: pointer; overflow: hidden; text-align: center;
    }
    .drop.over { border-color: var(--teal); background: var(--teal-soft); }
    .drop input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .drop img { width: 100%; max-height: 360px; object-fit: contain; }
    .drop-text { color: var(--muted); padding: 24px; }
    .bins { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .bin {
      display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px;
      border: 1px solid var(--line-strong); background: var(--surface); cursor: pointer; text-align: left;
    }
    .bin.on { border: 2px solid var(--teal); background: var(--teal-soft); }
    .run { align-self: flex-start; min-width: 160px; }
    figure { margin: 0; display: flex; flex-direction: column; gap: 6px; }
    .cam { width: 100%; border-radius: 12px; }
    @media (max-width: 1100px) { .chk { grid-template-columns: 1fr; } }
  `,
})
export class CheckPage implements OnDestroy {
  private readonly api = inject(ApiService);
  protected readonly store = inject(LabelStore);
  protected readonly file = signal<File | null>(null);
  protected readonly preview = signal<string | null>(null);
  protected readonly bin = signal('B4');
  protected readonly running = signal(false);
  protected readonly result = signal<Decision | null>(null);
  protected readonly dragOver = signal(false);

  protected onPick(ev: Event): void {
    this.setFile((ev.target as HTMLInputElement).files?.[0] ?? null);
  }

  protected onDrop(ev: DragEvent): void {
    ev.preventDefault();
    this.dragOver.set(false);
    this.setFile(ev.dataTransfer?.files?.[0] ?? null);
  }

  private setFile(f: File | null): void {
    if (this.preview()) URL.revokeObjectURL(this.preview()!);
    this.file.set(f);
    this.preview.set(f ? URL.createObjectURL(f) : null);
    this.result.set(null);
  }

  protected run(): void {
    const f = this.file();
    if (!f) return;
    this.running.set(true);
    this.api.predict(f, this.bin()).subscribe({
      next: (d) => { this.result.set(d); this.running.set(false); },
      error: () => this.running.set(false),
    });
  }

  ngOnDestroy(): void {
    if (this.preview()) URL.revokeObjectURL(this.preview()!);
  }
}
