import type { AgentRunDetail } from "@/types";

const STORAGE_KEY = "ai-cut-agent-runs-v2";
const MAX_RUNS = 40;

function readJson(text: string | null): AgentRunDetail[] {
  if (!text) {
    return [];
  }
  try {
    const parsed = JSON.parse(text) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is AgentRunDetail => Boolean(item && typeof item === "object" && "id" in item));
  } catch {
    return [];
  }
}

export function loadAgentRuns(): AgentRunDetail[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    return readJson(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return [];
  }
}

export function saveAgentRuns(runs: AgentRunDetail[]) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs.slice(0, MAX_RUNS)));
  } catch {
    // Ignore persistence failures.
  }
}

export function upsertAgentRun(run: AgentRunDetail) {
  const next = [run, ...loadAgentRuns().filter((item) => item.id !== run.id)].slice(0, MAX_RUNS);
  saveAgentRuns(next);
  return next;
}

export function clearAgentRuns() {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore persistence failures.
  }
}
