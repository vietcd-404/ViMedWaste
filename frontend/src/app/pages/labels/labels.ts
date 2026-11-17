import { Component, inject } from '@angular/core';
import { LabelStore } from '../../shared/bins';

@Component({
  selector: 'app-labels',
  template: `
    <div class="page">
      <h1>Bảng nhãn và hướng dẫn chụp</h1>
      <p class="page-sub">10 loại chất thải hệ thống nhận ra và thùng đúng của từng loại, theo Thông tư 20/2021/TT-BYT.</p>

      <section class="card">
        <h2>Bảng nhãn</h2>
        <div class="table-wrap">
          <table class="tbl">
            <thead><tr><th>Mã</th><th>Tên nhãn</th><th>Nhóm theo TT 20/2021</th><th>Thùng đúng</th><th>Ví dụ</th></tr></thead>
            <tbody>
              @for (l of store.labels(); track l.code) {
                <tr>
                  <td>{{ l.code }}</td>
                  <td>{{ l.name }}</td>
                  <td>{{ l.group_name }}</td>
                  <td class="bins">
                    @for (b of mainBin(l.correct_bins); track b) {
                      <span class="bin-chip" [style.background]="store.bin(b)?.color" [style.border-color]="store.bin(b)?.border"></span> {{ b }}
                    }
                  </td>
                  <td>{{ l.example }}</td>
                </tr>
              } @empty {
                <tr><td colspan="5" class="note">Chưa tải được bảng nhãn từ máy chủ.</td></tr>
              }
            </tbody>
          </table>
        </div>
        <p class="note">Bông, gạc, găng tay, dây truyền (L03–L05) bỏ vào hộp kháng thủng B1 cũng không bị cảnh báo, vì cùng là dòng chất thải lây nhiễm.</p>
      </section>

      <section class="card">
        <h2>Cách chụp ảnh để kết quả chính xác</h2>
        <div class="tips">
          @for (t of tips; track t.title) {
            <div class="tip"><b>{{ t.title }}</b><span>{{ t.text }}</span></div>
          }
        </div>
      </section>
    </div>
  `,
  styles: `
    .table-wrap { overflow-x: auto; }
    .bins { white-space: nowrap; }
    .tips { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
    .tip { background: #F3F5F4; border-radius: 14px; padding: 18px 20px; display: flex; flex-direction: column; gap: 4px; font-size: 16px; }
    @media (max-width: 1100px) { .tips { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 600px) { .tips { grid-template-columns: 1fr; } }
  `,
})
export class LabelsPage {
  protected readonly store = inject(LabelStore);
  protected readonly tips = [
    { title: 'Từ trên xuống', text: 'Cách miệng thùng 40–80 cm.' },
    { title: 'Thấy miệng thùng', text: 'Để nhận ra màu và loại thùng.' },
    { title: 'Đủ sáng, không rung', text: 'Không bật flash chiếu thẳng.' },
    { title: 'Không chụp người', text: 'Không để lộ tên người bệnh trên bao bì.' },
  ];

  /** Thùng chuẩn của nhãn: L03–L05 được phép cả B1 nhưng thùng chuẩn là B2. */
  protected mainBin(bins: string[]): string[] {
    return bins.length > 1 ? bins.filter((b) => b !== 'B1') : bins;
  }
}
