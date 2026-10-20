/**
 * Small per-browser storage for the theme choice and the session. Reads and writes are
 * wrapped because storage can be missing or blocked (private windows, native builds);
 * the app then simply starts signed out with the default theme.
 */
export const storage = {
  get(key: string): string | null {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  },
  set(key: string, value: string) {
    try {
      globalThis.localStorage?.setItem(key, value);
    } catch {
      // Not persisted; the choice still applies for this visit.
    }
  },
  remove(key: string) {
    try {
      globalThis.localStorage?.removeItem(key);
    } catch {
      // Nothing to clear.
    }
  },
};
