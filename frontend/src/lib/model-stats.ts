/** Offline evaluation stats from experiments — shown on analytics page */
export const MODEL_BENCHMARKS = {
  gcn: {
    name: "GCN (Graph Window)",
    f1: 0.61,
    recall: 1.0,
    precision: 0.44,
    rocAuc: 0.9,
    latencyMs: 0.2,
    confusion: [
      [5200, 800],
      [0, 1200],
    ],
  },
  gat: {
    name: "GAT (Graph Window)",
    f1: 0.64,
    recall: 0.98,
    precision: 0.47,
    rocAuc: 0.91,
    latencyMs: 0.35,
    confusion: [
      [5100, 900],
      [30, 1170],
    ],
  },
  rf: {
    name: "Random Forest (Flow)",
    f1: 0.9997,
    recall: 0.9994,
    precision: 0.9999,
    rocAuc: 0.9999,
    latencyMs: 0.05,
    confusion: [
      [5998, 1],
      [3, 5999],
    ],
  },
} as const;
