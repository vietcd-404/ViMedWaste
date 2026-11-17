import { dateTime, hhmm, pct, vnNumber } from './format';
import { applyDrag } from '../pages/station-config/station-config';

describe('định dạng kiểu Việt', () => {
  it('phần trăm dùng dấu phẩy thập phân', () => {
    expect(pct(0.78)).toBe('78%');
    expect(pct(0.785, 1)).toBe('78,5%');
    expect(pct(null)).toBe('–');
  });

  it('số có dấu phẩy thập phân và dấu chấm hàng nghìn', () => {
    expect(vnNumber(1.0, 1)).toBe('1,0');
    expect(vnNumber(1294)).toBe('1.294');
  });

  it('giờ HH:mm theo giờ máy', () => {
    const iso = new Date(2026, 10, 17, 9, 5).toISOString();
    expect(hhmm(iso)).toBe('09:05');
    expect(dateTime(iso)).toBe('09:05 · 17/11/2026');
    expect(hhmm('không phải ngày')).toBe('–');
  });
});

describe('kéo khung vùng thùng', () => {
  it('di chuyển nhưng không ra khỏi ảnh', () => {
    expect(applyDrag([0.8, 0.1, 0.2, 0.3], 'move', 0.5, -0.5)).toEqual([0.8, 0, 0.2, 0.3]);
  });

  it('đổi kích thước có giới hạn nhỏ nhất', () => {
    const [, , w, h] = applyDrag([0.1, 0.1, 0.3, 0.3], 'resize', -1, 0.2);
    expect(w).toBe(0.05);
    expect(h).toBeCloseTo(0.5);
  });
});
