// Centralized defaults for the ephemeral line CAPTCHA.

export const CANVAS_WIDTH_PX = 400;
export const CANVAS_HEIGHT_PX = 400;

export const TARGET_COMPLETION_TIME_MS = 3000;
export const PATH_TRAVEL_PX_RANGE = { min: 200, max: 300 };
export const MAX_GENTLE_BENDS = 2;

export const CHALLENGE_TTL_MS = 12000; // acceptable range 10–15s
export const TOO_FAST_THRESHOLD_MS = 1000;
export const MIN_SAMPLES = 20;

export const TRAIL_VISIBLE_MS = 400;
export const TRAIL_FADEOUT_MS = 600; // fades out after visible window

export const REQUIRED_COVERAGE_RATIO = 0.75; // 70–80% allowed; default to 75%
export const SPEED_CONSTANTITY_RATIO = 0.08;
export const MAX_ACCEL_PX_PER_S2 = 12000;

export type PointerProfile = 'mouse' | 'touch';

export interface PointerConfig {
  tolerancePx: number;
  lineThicknessPx: number;
}

export const POINTER_CONFIG: Record<PointerProfile, PointerConfig> = {
  mouse: { tolerancePx: 20, lineThicknessPx: 3 },
  touch: { tolerancePx: 30, lineThicknessPx: 6 },
};

export enum AttemptOutcomeReason {
  Success = 'success',
  TooFast = 'too_fast',
  Timeout = 'timeout',
  LowCoverage = 'low_coverage',
}

export interface AttemptLog {
  attemptId: string; // UUID
  sessionId: string; // UUID
  pointerType: PointerProfile | 'pen';
  osFamily?: string;
  browserFamily?: string;
  pathSeed: string;
  pathLengthPx: number;
  tolerancePx: number;
  ttlMs: number;
  startedAt: number; // epoch ms
  endedAt: number; // epoch ms
  durationMs: number;
  outcome: AttemptOutcomeReason;
  coverageRatio: number;
  meanSpeedPxPerSec?: number;
  maxSpeedPxPerSec?: number;
  pauseCount?: number;
  pauseDurationsMs?: number[];
  deviationStatsPx?: {
    mean: number;
    max: number;
  };
  trajectory?: Array<{ x: number; y: number; t: number }>;
}
