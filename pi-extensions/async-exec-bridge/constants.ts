export const JOB_TIMEOUT_MS = 30 * 60 * 1000;
export const MAX_CONCURRENT_JOBS = 3;
/** Bytes of tail injected into context. NOT the capture cap — 8 MiB of output
 *  in the prompt would cost minutes of prefill on a local model. */
export const ENVELOPE_TAIL_BYTES = 4 * 1024;
/** Bytes kept on disk. Never injected. */
export const CAPTURE_MAX_BYTES = 8 * 1024 * 1024;
export const HEARTBEAT_INTERVAL_MS = 10 * 1000;
export const LEASE_STALE_MS = 60 * 1000;
/** How long a reported, finished job stays on disk. Conservative on purpose:
 *  the run directory is the only durable evidence a job ever ran, so a week is
 *  long enough to still be investigating last Monday's failure. Running and
 *  unreported jobs are never pruned at any age. */
export const RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
/** Ceiling on kept records regardless of age, so a busy week cannot grow the
 *  run directory (and bg_status's output) without bound. */
export const MAX_KEPT_JOBS = 50;
