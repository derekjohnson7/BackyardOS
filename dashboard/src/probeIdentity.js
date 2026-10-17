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
