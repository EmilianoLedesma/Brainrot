export const GENERATION_PROVIDERS = {
  "claude-code": "Claude",
  codex: "Chat GPT",
};

export const DEFAULT_BRAINROT_LEVEL = 35;

export function brainrotBand(level) {
  return Math.min(4, Math.floor(level / 20));
}

export function brainrotSummary(level, copy) {
  return `${level}/100 · ${copy.levels[brainrotBand(level)].name}`;
}
