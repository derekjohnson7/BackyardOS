// Missing probe_id is the original single-probe firmware's Probe 1.
export function probeKey(deviceId, probeId = 1) {
  return JSON.stringify([deviceId, probeId ?? 1]);
}

export function groupReadings(rows, parseTimestamp) {
  const groups = new Map();
  for (const row of rows) {
    const key = probeKey(row.device_id, row.probe_id);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  for (const readings of groups.values()) {
    readings.sort((a, b) => parseTimestamp(a.timestamp) - parseTimestamp(b.timestamp));
  }
  return groups;
}

// One BME280 snapshot is repeated on each probe row. Display it once per cycle.
// Prefer the lowest available probe ID, then newest database row for that probe.
export function groupEnvironmentReadings(rows, parseTimestamp) {
  const nodes = new Map();
  for (const row of rows) {
    const timestamp = parseTimestamp(row.timestamp);
    if (!timestamp || !Number.isFinite(timestamp.getTime())) continue;
    if (!nodes.has(row.device_id)) nodes.set(row.device_id, new Map());
    const cycles = nodes.get(row.device_id);
    const key = timestamp.getTime();
    const previous = cycles.get(key);
    const probe = row.probe_id ?? 1;
    const previousProbe = previous?.probe_id ?? 1;
    if (!previous || probe < previousProbe ||
        (probe === previousProbe && (row.id ?? 0) > (previous.id ?? 0))) {
      cycles.set(key, row);
    }
  }
  return new Map([...nodes].map(([device, cycles]) => [
    device,
    [...cycles.values()].sort((a, b) => parseTimestamp(a.timestamp) - parseTimestamp(b.timestamp)),
  ]));
}
