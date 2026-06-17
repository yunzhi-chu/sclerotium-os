/** Web Worker: Holographic fractal encoder for event stream compression. */

interface EncoderMessage {
  type: "encode";
  events: EventData[];
}

interface EncoderResult {
  type: "hologram";
  size_bytes: number;
  original_count: number;
  compression_ratio: number;
  hologram: number[];
  anomaly_scores: number[];
}

interface EventData {
  event_type: string;
  timestamp: number;
  value: number;
  metadata?: Record<string, number>;
}

const FREQ_BANDS = 8;
const BAND_SIZE = 128;

class HolographicEncoder {
  private buffer: Float64Array;
  private count: number = 0;

  constructor() {
    this.buffer = new Float64Array(FREQ_BANDS * BAND_SIZE);
  }

  encode(events: EventData[]): EncoderResult {
    this.buffer.fill(0);

    for (const event of events) {
      const band = this.eventToBand(event.event_type);
      const offset = band * BAND_SIZE;
      const pos = this.count % BAND_SIZE;

      // Interference pattern encoding
      const phase = (event.timestamp % 1000) / 1000 * Math.PI * 2;
      const amp = Math.tanh(event.value);
      this.buffer[offset + pos] += amp * Math.cos(phase + pos * 0.1);
    }

    // Extract hologram as compressed representation
    const hologram: number[] = [];
    for (let b = 0; b < FREQ_BANDS; b++) {
      let sum = 0;
      let energy = 0;
      for (let i = 0; i < BAND_SIZE; i++) {
        sum += this.buffer[b * BAND_SIZE + i];
        energy += this.buffer[b * BAND_SIZE + i] ** 2;
      }
      hologram.push(sum / BAND_SIZE);
      hologram.push(Math.sqrt(energy / BAND_SIZE));
    }

    // Anomaly scores per band
    const anomalyScores = hologram
      .filter((_, i) => i % 2 === 1)
      .map((e) => Math.min(1, e * 10));

    const sizeBytes = hologram.length * 8;
    const compressionRatio = events.length > 0
      ? (events.length * 64) / sizeBytes
      : 0;

    this.count += events.length;

    return {
      type: "hologram",
      size_bytes: sizeBytes,
      original_count: events.length,
      compression_ratio: compressionRatio,
      hologram,
      anomaly_scores: anomalyScores,
    };
  }

  private eventToBand(type: string): number {
    const bandMap: Record<string, number> = {
      tick: 0,
      signal: 1,
      debate: 2,
      research: 3,
      trading: 4,
      risk: 5,
      emergence: 6,
      system: 7,
    };
    return bandMap[type] ?? 7;
  }
}

const encoder = new HolographicEncoder();

self.onmessage = (e: MessageEvent<EncoderMessage>) => {
  if (e.data.type !== "encode") return;
  const result = encoder.encode(e.data.events);
  self.postMessage(result);
};

export {};
