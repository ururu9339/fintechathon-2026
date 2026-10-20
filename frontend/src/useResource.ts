import { DependencyList, useCallback, useEffect, useState } from "react";

/** Loads data on mount and whenever `deps` change; keeps the last good value while reloading. */
export function useResource<T>(load: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Wrap the loader so a stable function (e.g. `api.payments`) still reloads when deps change.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(() => load(), deps);

  const reload = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    run()
      .then((value) => {
        if (cancelled) return;
        setData(value);
        setError(null);
      })
      .catch((reason: Error) => !cancelled && setError(reason.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [run]);

  useEffect(reload, [reload]);

  return { data, error, loading, reload };
}
