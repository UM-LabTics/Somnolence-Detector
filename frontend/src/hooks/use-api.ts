"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseApiOptions {
  refreshInterval?: number;
  deps?: unknown[];
}

interface UseApiReturn<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  refresh: () => void;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  options?: UseApiOptions
): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const doFetch = useCallback(async (abortedRef?: { current: boolean }) => {
    try {
      const result = await fetcherRef.current();
      if (abortedRef?.current) return;
      setData(result);
      setError(null);
    } catch (err) {
      if (abortedRef?.current) return;
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      if (!abortedRef?.current) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const aborted = { current: false };
    setIsLoading(true);
    doFetch(aborted);

    let interval: ReturnType<typeof setInterval> | undefined;
    if (options?.refreshInterval) {
      interval = setInterval(() => doFetch(aborted), options.refreshInterval);
    }

    return () => {
      aborted.current = true;
      if (interval) clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...(options?.deps || []), options?.refreshInterval]);

  const refresh = useCallback(() => {
    setIsLoading(true);
    doFetch();
  }, [doFetch]);

  return { data, error, isLoading, refresh };
}
