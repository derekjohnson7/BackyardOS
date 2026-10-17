import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupReadings, probeKey } from '../src/probeIdentity.js';

test('legacy Probe 1 continues while other probes and other nodes stay separate', () => {
  const rows = [
    {device_id: 'node-01', probe_id: 1, timestamp: '2026-10-17T12:00:00Z', soil_moisture_pct: 20},
    {device_id: 'node-01', probe_id: 2, timestamp: '2026-10-17T12:00:00Z', soil_moisture_pct: 80},
    {device_id: 'node-02', timestamp: '2026-10-17T12:00:00Z', soil_moisture_pct: 45},
    {device_id: 'node-01', timestamp: '2026-10-17T11:00:00Z', soil_moisture_pct: 25},
  ];
  const grouped = groupReadings(rows, (ts) => new Date(ts));
  assert.equal(grouped.size, 3);
  assert.deepEqual(grouped.get(probeKey('node-01', 1)).map(r => r.soil_moisture_pct), [25, 20]);
  assert.equal(grouped.get(probeKey('node-01', 2))[0].soil_moisture_pct, 80);
  assert.equal(grouped.get(probeKey('node-02', 1))[0].soil_moisture_pct, 45);
});
