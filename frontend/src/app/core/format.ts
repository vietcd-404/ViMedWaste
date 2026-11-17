import { Pipe, PipeTransform } from '@angular/core';

const VN = 'vi-VN';

/** 0.78 → "78%"; 0.785 → "78,5%" khi cần một chữ số. */
export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  return new Intl.NumberFormat(VN, { maximumFractionDigits: digits, minimumFractionDigits: digits })
    .format(value * 100) + '%';
}

/** Số kiểu Việt: dấu phẩy thập phân, dấu chấm hàng nghìn. */
export function vnNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  return new Intl.NumberFormat(VN, { maximumFractionDigits: digits, minimumFractionDigits: digits })
    .format(value);
}

/** ISO → "HH:mm" theo giờ máy. */
export function hhmm(iso: string | null | undefined): string {
  if (!iso) return '–';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '–';
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/** ISO → "HH:mm · dd/MM/yyyy". */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '–';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '–';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${hhmm(iso)} · ${dd}/${mm}/${d.getFullYear()}`;
}

@Pipe({ name: 'pct' })
export class PctPipe implements PipeTransform {
  transform(value: number | null | undefined, digits = 0): string {
    return pct(value, digits);
  }
}

@Pipe({ name: 'vn' })
export class VnNumberPipe implements PipeTransform {
  transform(value: number | null | undefined, digits = 0): string {
    return vnNumber(value, digits);
  }
}

@Pipe({ name: 'hhmm' })
export class HhmmPipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    return hhmm(value);
  }
}

@Pipe({ name: 'dateTime' })
export class DateTimePipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    return dateTime(value);
  }
}
