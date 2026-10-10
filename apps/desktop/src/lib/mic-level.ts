/** Shared RMS scale for desktop mic meters (recorder, barge-in, live voice). */

const BYTE_RMS_FULL_SCALE = 42
const FLOAT_RMS_FULL_SCALE = BYTE_RMS_FULL_SCALE / 128

/** 8-bit time-domain analyser buffer → 0..1, same scale as the chained recorder. */
export function rmsLevelFromByteTimeDomain(data: Uint8Array): number {
  if (data.length === 0) {
    return 0
  }

  let sum = 0

  for (const value of data) {
    const centered = value - 128
    sum += centered * centered
  }

  return Math.min(1, Math.sqrt(sum / data.length) / BYTE_RMS_FULL_SCALE)
}

/** Float PCM (−1..1) → 0..1 on the same scale as `rmsLevelFromByteTimeDomain`. */
export function rmsLevelFromFloatSamples(data: ArrayLike<number>): number {
  if (data.length === 0) {
    return 0
  }

  let sum = 0

  for (let index = 0; index < data.length; index += 1) {
    const sample = data[index] ?? 0
    sum += sample * sample
  }

  return Math.min(1, Math.sqrt(sum / data.length) / FLOAT_RMS_FULL_SCALE)
}
