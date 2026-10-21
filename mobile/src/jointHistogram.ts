/** Joint histograms of 100 vectors stored flat in row-major order. */
export function jointHistogram(
  flat: number[],
  dimensions: number,
  bins: number,
) {
  const limit = dimensions === 1 ? 50 : dimensions === 2 ? 12 : 8;
  if (
    !Number.isInteger(dimensions) ||
    dimensions < 1 ||
    dimensions > 3 ||
    flat.length !== 100 * dimensions ||
    !flat.every(Number.isFinite) ||
    !Number.isInteger(bins) ||
    bins < 1 ||
    bins > limit
  )
    throw Error('Histograma conjunto inválido.');
  const axes = Array.from({ length: dimensions }, (_, d) => {
    const values = Array.from(
      { length: 100 },
      (_, r) => flat[r * dimensions + d],
    );
    let min = Math.min(...values),
      max = Math.max(...values);
    if (min === max) {
      const pad = Math.max(Math.abs(min) * 0.01, 0.5);
      min -= pad;
      max += pad;
    }
    return {
      min,
      max,
      width: (max - min) / bins,
      mean: values.reduce((a, b) => a + b, 0) / 100,
    };
  });
  const counts = new Map<string, { indices: number[]; frequency: number }>();
  for (let r = 0; r < 100; r++) {
    const indices = axes.map((a, d) =>
      Math.max(
        0,
        Math.min(
          bins - 1,
          Math.floor((flat[r * dimensions + d] - a.min) / a.width),
        ),
      ),
    );
    const key = indices.join(',');
    const cell = counts.get(key) || { indices, frequency: 0 };
    cell.frequency += 0.01;
    counts.set(key, cell);
  }
  const cells = [...counts.values()].sort((a, b) =>
    a.indices.join(',').localeCompare(b.indices.join(',')),
  );
  return { axes, cells, peak: Math.max(...cells.map(c => c.frequency)), bins };
}
