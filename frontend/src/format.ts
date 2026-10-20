const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** "MYR 84,600", or "−MYR 5,800" for negatives. */
export function myr(value: number): string {
  const sign = value < 0 ? "−" : "";
  return `${sign}MYR ${Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** "84,600" without the currency, for table cells. */
export function amount(value: number): string {
  const sign = value < 0 ? "−" : "";
  return sign + Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

/** Parses an ISO date ("2026-10-16") without shifting it into the browser's time zone. */
function parts(iso: string): [number, number, number] {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return [year, month, day];
}

/** "16 Nov", or "16 Nov 2026" with the year. */
export function dayMonth(iso: string, withYear = false): string {
  const [year, month, day] = parts(iso);
  return `${day} ${MONTHS[month - 1]}${withYear ? ` ${year}` : ""}`;
}

/** "16–22 Nov", or "30 Nov – 6 Dec" across months; appends the year when asked. */
export function weekRange(iso: string, withYear = false): string {
  const [year, month, day] = parts(iso);
  const end = new Date(Date.UTC(year, month - 1, day + 6));
  const endMonth = end.getUTCMonth() + 1;
  const suffix = withYear ? ` ${end.getUTCFullYear()}` : "";
  return endMonth === month
    ? `${day}–${end.getUTCDate()} ${MONTHS[month - 1]}${suffix}`
    : `${day} ${MONTHS[month - 1]} – ${end.getUTCDate()} ${MONTHS[endMonth - 1]}${suffix}`;
}

/** "Friday, 16 Oct 2026" */
export function longDate(iso: string): string {
  const [year, month, day] = parts(iso);
  const weekday = WEEKDAYS[new Date(Date.UTC(year, month - 1, day)).getUTCDay()];
  return `${weekday}, ${day} ${MONTHS[month - 1]} ${year}`;
}

/** "09:41" from an ISO timestamp, in the timestamp's own offset (MYT). */
export function clock(iso: string): string {
  const match = iso.match(/T(\d{2}):(\d{2})/);
  return match ? `${match[1]}:${match[2]}` : "";
}

/** "80k" axis labels. */
export function compact(value: number): string {
  return value === 0 ? "0" : `${Math.round(value / 1000)}k`;
}
