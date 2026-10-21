export const GENERATION_PROVIDERS = {
  "claude-code": "Claude",
  codex: "Chat GPT",
};

// Persist the existing API values, but expose five discrete choices in the UI.
export const BRAINROT_LEVELS = [0, 25, 50, 75, 100];
export const DEFAULT_BRAINROT_LEVEL = BRAINROT_LEVELS[1];

export function brainrotBand(level) {
  return Math.max(0, Math.min(4, Math.floor(level / 20)));
}

export function brainrotSummary(level, copy) {
  return copy.levels[brainrotBand(level)].name;
}
