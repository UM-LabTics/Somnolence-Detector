"use client";

import { useSyncExternalStore } from "react";

export function useNow(intervalMs = 1000): number {
  return useSyncExternalStore(
    (callback) => {
      const id = setInterval(callback, intervalMs);
      return () => clearInterval(id);
    },
    () => Date.now(),
    () => 0
  );
}
