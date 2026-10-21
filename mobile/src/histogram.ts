export function histogram(values: number[], bins: number) {
  if (
    !values.length ||
    !values.every(Number.isFinite) ||
    !Number.isInteger(bins) ||
    bins < 1 ||
    bins > 50
  )
    throw Error('Histograma inválido.');
  let min = Math.min(...values),
    max = Math.max(...values);
  if (min === max) {
    const pad = Math.max(Math.abs(min) * 0.01, 0.5);
    min -= pad;
    max += pad;
  }
  const width = (max - min) / bins,
    counts = Array<number>(bins).fill(0);
  values.forEach(
    x =>
      counts[Math.max(0, Math.min(bins - 1, Math.floor((x - min) / width)))]++,
  );
  return { min, max, width, frequencies: counts.map(n => n / values.length) };
}
