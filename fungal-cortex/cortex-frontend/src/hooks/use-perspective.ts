import { useEffect, useRef, useCallback } from "react";

export function usePerspective(
  _containerId: string
): {
  load: () => Promise<unknown>;
  isLoaded: () => boolean;
} {
  const moduleRef = useRef<unknown>(null);

  const load = useCallback(async () => {
    if (moduleRef.current) return moduleRef.current;
    try {
      const mod = await import("@finos/perspective");
      moduleRef.current = mod;
      return mod;
    } catch {
      console.warn("Perspective not available");
      return null;
    }
  }, []);

  useEffect(() => {
    return () => {
      moduleRef.current = null;
    };
  }, []);

  return {
    load,
    isLoaded: () => moduleRef.current !== null,
  };
}
