import { describe, expect, it } from 'vitest'

import { rmsLevelFromByteTimeDomain, rmsLevelFromFloatSamples } from './mic-level'

describe('mic RMS helpers', () => {
  it('reports silence as zero on both byte-domain and float PCM', () => {
    expect(rmsLevelFromByteTimeDomain(new Uint8Array(8).fill(128))).toBe(0)
    expect(rmsLevelFromFloatSamples(new Float32Array(8))).toBe(0)
    expect(rmsLevelFromByteTimeDomain(new Uint8Array())).toBe(0)
    expect(rmsLevelFromFloatSamples([])).toBe(0)
  })

  it('scales float PCM to the same 0..1 reading as the byte-domain analyser', () => {
    const amplitude = 21
    const bytes = new Uint8Array([128 + amplitude, 128 - amplitude])
    const floats = new Float32Array([amplitude / 128, -amplitude / 128])

    expect(rmsLevelFromFloatSamples(floats)).toBeCloseTo(rmsLevelFromByteTimeDomain(bytes), 5)
    expect(rmsLevelFromByteTimeDomain(bytes)).toBeGreaterThan(0)
    expect(rmsLevelFromByteTimeDomain(bytes)).toBeLessThanOrEqual(1)
  })

  it('clamps a full-scale signal to 1', () => {
    expect(rmsLevelFromByteTimeDomain(new Uint8Array([0, 255]))).toBe(1)
    expect(rmsLevelFromFloatSamples(new Float32Array([1, -1]))).toBe(1)
  })
})
