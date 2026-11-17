import { Component, ElementRef, OnInit, computed, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { VnNumberPipe } from '../../core/format';
import { Box, Decision, Settings, Station, Zone } from '../../core/models';
import { LabelStore } from '../../shared/bins';
import { DecisionView } from '../../shared/decision-view';

type DragMode = 'move' | 'resize';
const MIN_SIZE = 0.05;

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

/** Di chuyển hoặc đổi kích thước khung theo độ dời (tỷ lệ 0..1), luôn nằm trong ảnh. */
export function applyDrag(box: Box, mode: DragMode, dx: number, dy: number): Box {
  const [x, y, w, h] = box;
  if (mode === 'move') {
    return [clamp(x + dx, 0, 1 - w), clamp(y + dy, 0, 1 - h), w, h];
  }
  return [x, y, clamp(w + dx, MIN_SIZE, 1 - x), clamp(h + dy, MIN_SIZE, 1 - y)];
}

@Component({
  selector: 'app-station-config',
  imports: [FormsModule, VnNumberPipe, DecisionView],
  templateUrl: './station-config.html',
  styleUrl: './station-config.scss',
})
export class StationConfigPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly store = inject(LabelStore);
  private readonly canvas = viewChild<ElementRef<HTMLDivElement>>('canvas');

  protected readonly stations = signal<Station[]>([]);
  protected readonly stationId = signal<string>('');
  protected readonly zones = signal<Zone[]>([]);
  protected readonly settings = signal<Settings>({ still_seconds: 1, motion_sensitivity: 0.5, buzzer_volume: 0.6, dry_run: false });
  protected readonly selected = signal<number | null>(null);
  protected readonly snapshot = signal<string>('');
  protected readonly saving = signal(false);
  protected readonly saved = signal(false);
  protected readonly testing = signal(false);
  protected readonly testResult = signal<Decision | null>(null);
  protected testFile: File | null = null;

  protected readonly station = computed(() => this.stations().find((s) => s.id === this.stationId()) ?? null);

  private drag: { zoneNo: number; mode: DragMode; startX: number; startY: number; box: Box; rect: DOMRect } | null = null;

  ngOnInit(): void {
    this.api.stations().subscribe({
      next: (list) => {
        this.stations.set(list);
        if (list.length) this.select(list[0].id);
      },
      error: () => {},
    });
  }

  protected select(id: string): void {
    this.stationId.set(id);
    const s = this.stations().find((x) => x.id === id);
    if (!s) return;
    this.zones.set(s.zones.map((z) => ({ ...z, box: [...z.box] as Box })));
    this.settings.set({ ...s.settings });
    this.selected.set(s.zones[0]?.zone_no ?? null);
    this.snapshot.set(this.api.snapshotUrl(id));
    this.testResult.set(null);
    this.saved.set(false);
  }

  protected setBin(zoneNo: number, bin: string): void {
    this.zones.update((zs) => zs.map((z) => (z.zone_no === zoneNo ? { ...z, bin_type: bin } : z)));
    this.saved.set(false);
  }

  protected addZone(): void {
    const next = Math.max(0, ...this.zones().map((z) => z.zone_no)) + 1;
    this.zones.update((zs) => [...zs, { zone_no: next, bin_type: 'B4', box: [0.38, 0.3, 0.24, 0.4] }]);
    this.selected.set(next);
    this.saved.set(false);
  }

  protected removeZone(zoneNo: number): void {
    this.zones.update((zs) => zs.filter((z) => z.zone_no !== zoneNo));
    if (this.selected() === zoneNo) this.selected.set(this.zones()[0]?.zone_no ?? null);
    this.saved.set(false);
  }

  protected setSetting<K extends keyof Settings>(key: K, value: Settings[K]): void {
    this.settings.update((s) => ({ ...s, [key]: value }));
    this.saved.set(false);
  }

  protected startDrag(ev: PointerEvent, zone: Zone, mode: DragMode): void {
    const el = this.canvas()?.nativeElement;
    if (!el) return;
    ev.preventDefault();
    ev.stopPropagation();
    (ev.target as Element).setPointerCapture?.(ev.pointerId);
    this.selected.set(zone.zone_no);
    this.drag = { zoneNo: zone.zone_no, mode, startX: ev.clientX, startY: ev.clientY, box: zone.box, rect: el.getBoundingClientRect() };
  }

  protected onMove(ev: PointerEvent): void {
    const d = this.drag;
    if (!d) return;
    const dx = (ev.clientX - d.startX) / d.rect.width;
    const dy = (ev.clientY - d.startY) / d.rect.height;
    const box = applyDrag(d.box, d.mode, dx, dy);
    this.zones.update((zs) => zs.map((z) => (z.zone_no === d.zoneNo ? { ...z, box } : z)));
    this.saved.set(false);
  }

  protected endDrag(): void {
    this.drag = null;
  }

  /** Bàn phím: mũi tên dời khung đang chọn 1%, Shift+mũi tên đổi kích thước. */
  protected onKey(ev: KeyboardEvent, zone: Zone): void {
    const step = 0.01;
    const map: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step],
    };
    const delta = map[ev.key];
    if (!delta) return;
    ev.preventDefault();
    const box = applyDrag(zone.box, ev.shiftKey ? 'resize' : 'move', delta[0], delta[1]);
    this.zones.update((zs) => zs.map((z) => (z.zone_no === zone.zone_no ? { ...z, box } : z)));
    this.saved.set(false);
  }

  protected save(): void {
    const id = this.stationId();
    if (!id) return;
    this.saving.set(true);
    this.api.saveConfig(id, this.zones(), this.settings()).subscribe({
      next: (s) => {
        this.stations.update((list) => list.map((x) => (x.id === s.id ? s : x)));
        this.saving.set(false);
        this.saved.set(true);
      },
      error: () => this.saving.set(false),
    });
  }

  protected pickFile(ev: Event): void {
    this.testFile = (ev.target as HTMLInputElement).files?.[0] ?? null;
  }

  protected testCapture(): void {
    const id = this.stationId();
    const zone = this.selected();
    if (!id || zone === null) return;
    this.testing.set(true);
    this.testResult.set(null);
    this.api.testCapture(id, zone, this.testFile ?? undefined).subscribe({
      next: (d) => { this.testResult.set(d); this.testing.set(false); },
      error: () => this.testing.set(false),
    });
  }
}
