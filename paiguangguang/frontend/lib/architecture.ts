import { getJson } from "@/lib/api";
import type { ArchitectureGraphData } from "@/types/architecture";

export function getSystemArchitectureGraph() {
  return getJson<ArchitectureGraphData>("/api/v1/architecture/graphs/system");
}
