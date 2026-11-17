import { Component } from '@angular/core';

/** Sơ đồ luồng tự động và sơ đồ lắp đặt một trạm, vẽ bằng SVG. */
@Component({
  selector: 'app-system',
  templateUrl: './system.html',
  styleUrl: './system.scss',
})
export class SystemPage {
  protected readonly points = [
    { n: 1, title: 'Camera góc rộng', text: 'gắn trên tay đỡ, chĩa thẳng xuống, nhìn được cả 4 miệng thùng.' },
    { n: 2, title: 'Dải LED', text: 'chiếu sáng cố định để ảnh ổn định ngày và đêm.' },
    { n: 3, title: 'Raspberry Pi', text: 'chạy mô hình ONNX INT8 ngay tại chỗ, không cần GPU.' },
    { n: 4, title: 'Đèn và còi trên từng thùng.', text: 'Khi bỏ sai, đèn của đúng thùng đó sáng đỏ và kêu bíp ngắn.' },
    { n: 5, title: 'Wi-Fi:', text: 'chỉ gửi nhật ký sự kiện và ảnh vùng thùng về Dashboard, không gửi video.' },
    { n: 6, title: 'Vùng nhìn', text: 'chỉ chứa miệng thùng; ảnh chụp sau khi tay đã rút ra, không ghi hình người.' },
  ];

  protected readonly badges = [
    { n: 1, x: 490, y: 184 }, { n: 2, x: 317, y: 228 }, { n: 3, x: 224, y: 587 },
    { n: 4, x: 490, y: 439 }, { n: 5, x: 323, y: 587 }, { n: 6, x: 591, y: 394 },
  ];
}
