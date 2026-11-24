import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ApiService } from '../../core/api.service';
import { dateTime, pct, vnNumber } from '../../core/format';
import { EvalMetrics, TrainingReport } from '../../core/models';

interface Step {
  id: string;
  no: number;
  phase: string;          // bước trong quy trình 6 bước
  title: string;
  metric: string;
}

/** Trang "Huấn luyện mô hình": sơ đồ luồng train + số liệu thật của lần train gần nhất. */
@Component({
  selector: 'app-training',
  templateUrl: './training.html',
  styleUrl: './training.scss',
})
export class TrainingPage implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly report = signal<TrainingReport | null>(null);
  protected readonly loading = signal(true);
  protected readonly pct = pct;
  protected readonly vn = vnNumber;
  protected readonly dateTime = dateTime;

  /** Cấu hình cố định trong src/vimedwaste/training/train_mw40.py (không nằm trong file kết quả). */
  protected readonly headConfig = [
    ['Kiến trúc', 'Linear 1280 → 10 (12.810 tham số học)'],
    ['Đầu ra', '10 sigmoid độc lập (đa nhãn), không dùng softmax'],
    ['Hàm mất mát', 'BCEWithLogits = cực đại hợp lý (MLE) nhãn Bernoulli'],
    ['Tối ưu', 'AdamW, learning rate 0,001'],
    ['Regularization', 'Weight decay 1e-4 (L2)'],
    ['Mini-batch', '64 ảnh, xáo trộn mỗi epoch'],
    ['Dừng sớm', 'Theo mAP val, chờ 10 epoch, tối đa 300'],
    ['Số lần chạy', '3 seed (0, 1, 2), giữ seed tốt nhất'],
  ];

  protected readonly baselineNames: Record<string, string> = {
    muc_san_tan_suat: 'Mức sàn (đoán theo tần suất)',
    logistic_regression: 'Logistic Regression',
    linear_svc: 'Linear SVM',
    knn_k5: 'KNN (k = 5)',
    random_forest: 'Random Forest (300 cây)',
  };

  protected readonly activeLabels = computed(() => Object.keys(this.report()?.data?.positives_train ?? {}));

  protected readonly baselines = computed(() =>
    Object.entries(this.report()?.baselines_val ?? {}).map(([key, m]) => ({ key, name: this.baselineNames[key] ?? key, m })));

  /** Gom ngưỡng Bayes theo giá trị: mỗi nhóm chi phí một thanh. */
  protected readonly thresholdGroups = computed(() => {
    const groups = new Map<number, string[]>();
    for (const [code, t] of Object.entries(this.report()?.thresholds_bayes ?? {})) {
      const key = Math.round(t * 1e6) / 1e6;
      groups.set(key, [...(groups.get(key) ?? []), code]);
    }
    return [...groups.entries()].sort((a, b) => a[0] - b[0]).map(([t, codes]) => ({
      t, codes: codes.length > 2 ? `${codes[0]}–${codes[codes.length - 1]}` : codes.join(', '),
      cfn: Math.round(1 / t - 1),
    }));
  });

  protected readonly steps = computed<Step[]>(() => {
    const r = this.report();
    const d = r?.data;
    const m = r?.main_model;
    return [
      { id: 'du-lieu', no: 1, phase: 'Bước 2', title: 'Dữ liệu',
        metric: d ? `${this.vn(d.n_train)} train · ${this.vn(d.n_val)} val · ${this.vn(d.n_ood_near)} OOD` : '–' },
      { id: 'tien-xu-ly', no: 2, phase: 'Bước 2', title: 'Tiền xử lý ảnh', metric: '224 × 224 · chuẩn hóa ImageNet' },
      { id: 'dac-trung', no: 3, phase: 'Bước 3', title: 'Trích đặc trưng', metric: 'EfficientNet-B0 → 1280 số' },
      { id: 'baseline', no: 4, phase: 'Bước 3', title: 'Baseline cổ điển', metric: `${this.baselines().length} mô hình so sánh` },
      { id: 'mo-hinh', no: 5, phase: 'Bước 4', title: 'Mô hình chính',
        metric: m ? `mAP ${this.vn(m.val_mAP_3_seed.mean, 2)} ± ${this.vn(m.val_mAP_3_seed.std, 2)}` : '–' },
      { id: 'hieu-chuan', no: 6, phase: 'Bước 5', title: 'Hiệu chuẩn & ngưỡng',
        metric: m ? `T = ${this.vn(m.temperature, 3)}` : '–' },
      { id: 'lop-mo', no: 7, phase: 'Bước 5', title: 'Lớp mở (vật lạ)',
        metric: m ? `AUROC ${this.vn(m.open_set.auroc_val_vs_ood_near, 2)}` : '–' },
      { id: 'onnx', no: 8, phase: 'Triển khai', title: 'Xuất ONNX',
        metric: r?.onnx ? `${this.vn(r.onnx.size_mb, 1)} MB` : '–' },
    ];
  });

  ngOnInit(): void {
    this.api.training().subscribe({
      next: (r) => { this.report.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  protected go(id: string): void {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  protected isFloor(key: string): boolean {
    return key === 'muc_san_tan_suat';
  }

  protected apList(m: EvalMetrics): string {
    return Object.entries(m.ap).map(([k, v]) => `${k} ${this.vn(v, 2)}`).join(' · ');
  }
}
