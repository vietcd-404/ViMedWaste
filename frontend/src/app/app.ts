import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ApiService } from './core/api.service';
import { ModelInfo } from './core/models';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  protected readonly api = inject(ApiService);
  protected readonly model = signal<ModelInfo | null>(null);

  protected readonly nav = [
    { path: '/tong-quan', text: 'Tổng quan' },
    { path: '/su-kien', text: 'Sự kiện' },
    { path: '/cau-hinh-tram', text: 'Cấu hình trạm' },
    { path: '/kiem-tra', text: 'Kiểm tra thùng' },
    { path: '/huan-luyen', text: 'Huấn luyện mô hình' },
    { path: '/bang-nhan', text: 'Bảng nhãn' },
    { path: '/he-thong', text: 'Cách hoạt động' },
  ];

  ngOnInit(): void {
    this.api.model().subscribe({ next: (m) => this.model.set(m), error: () => this.model.set(null) });
  }

  protected modelLine(m: ModelInfo): string {
    const backbone = m.backbone === 'efficientnet_b0' ? 'EfficientNet-B0' : (m.backbone ?? 'Mô hình');
    return `${backbone} · ONNX`;
  }

  protected externalOnly(m: ModelInfo): boolean {
    return !!m.trained_on && m.trained_on !== 'vimedwaste';
  }
}
