/** Minimal type declarations for @finos/perspective dynamic import. */
declare module "@finos/perspective" {
  interface PerspectiveWorker {
    table?: (schema: Record<string, string>) => PerspectiveTable;
  }
  interface PerspectiveTable {
    update?: (data: unknown) => Promise<void>;
    delete?: () => Promise<void>;
  }
  const perspective: {
    worker?: () => PerspectiveWorker;
  } & Record<string, unknown>;
  export default perspective;
}
