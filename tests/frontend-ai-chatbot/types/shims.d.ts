// Minimal shims to satisfy the TypeScript language server for test-only imports
declare module "ai";
declare module "date-fns" {
  export function getUnixTime(date: Date): number;
}
