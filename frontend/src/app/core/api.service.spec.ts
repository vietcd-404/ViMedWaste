import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let api: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lọc sự kiện chỉ gửi tham số có giá trị', () => {
    api.events({ status: 'CANH_BAO', station_id: '', limit: 8 }).subscribe();
    const req = http.expectOne((r) => r.url === '/api/events');
    expect(req.request.params.get('status')).toBe('CANH_BAO');
    expect(req.request.params.has('station_id')).toBeFalse();
    expect(req.request.params.get('limit')).toBe('8');
    req.flush([]);
  });

  it('gửi ảnh và loại thùng dạng multipart khi nhận dạng', () => {
    const file = new File(['x'], 'a.jpg', { type: 'image/jpeg' });
    api.predict(file, 'B4').subscribe();
    const req = http.expectOne('/api/predict');
    expect(req.request.method).toBe('POST');
    const body = req.request.body as FormData;
    expect(body.get('bin_type')).toBe('B4');
    expect(body.get('image')).toBeTruthy();
    req.flush({});
  });

  it('báo lỗi thân thiện khi máy chủ tắt', () => {
    api.overview().subscribe({ error: () => {} });
    http.expectOne('/api/stats/overview').error(new ProgressEvent('error'), { status: 0 });
    expect(api.lastError()).toContain('Không kết nối được máy chủ');
  });

  it('lưu cấu hình bằng PUT với vùng và thiết lập', () => {
    const settings = { still_seconds: 1, motion_sensitivity: 0.5, buzzer_volume: 0.6, dry_run: false };
    api.saveConfig('tram-01', [{ zone_no: 1, bin_type: 'B1', box: [0, 0, 0.2, 0.2] }], settings).subscribe();
    const req = http.expectOne('/api/stations/tram-01/config');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body.zones.length).toBe(1);
    req.flush({});
  });
});
