import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'tong-quan' },
  {
    path: 'tong-quan', title: 'Tổng quan · ViMedWaste',
    loadComponent: () => import('./pages/overview/overview').then((m) => m.OverviewPage),
  },
  {
    path: 'su-kien', title: 'Sự kiện · ViMedWaste',
    loadComponent: () => import('./pages/events/events').then((m) => m.EventsPage),
  },
  {
    path: 'su-kien/:id', title: 'Chi tiết sự kiện · ViMedWaste',
    loadComponent: () => import('./pages/event-detail/event-detail').then((m) => m.EventDetailPage),
  },
  {
    path: 'cau-hinh-tram', title: 'Cấu hình trạm · ViMedWaste',
    loadComponent: () => import('./pages/station-config/station-config').then((m) => m.StationConfigPage),
  },
  {
    path: 'kiem-tra', title: 'Kiểm tra thùng · ViMedWaste',
    loadComponent: () => import('./pages/check/check').then((m) => m.CheckPage),
  },
  {
    path: 'bang-nhan', title: 'Bảng nhãn · ViMedWaste',
    loadComponent: () => import('./pages/labels/labels').then((m) => m.LabelsPage),
  },
  {
    path: 'he-thong', title: 'Cách hệ thống hoạt động · ViMedWaste',
    loadComponent: () => import('./pages/system/system').then((m) => m.SystemPage),
  },
  { path: '**', redirectTo: 'tong-quan' },
];
