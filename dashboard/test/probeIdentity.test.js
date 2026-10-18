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

test('shared environmental charts have one point per node and timestamp without changing soil histories', async () => {
  const { groupEnvironmentReadings } = await import('../src/probeIdentity.js');
  const rows = [
    ...[4, 2, 1, 3].map(probe_id => ({device_id: 'node-01', probe_id, id: probe_id,
      timestamp: '2026-10-17T12:00:00Z', temperature_c: 24, soil_moisture_pct: probe_id * 10})),
    {device_id: 'node-01', probe_id: 2, timestamp: '2026-10-17T12:10:00Z', temperature_c: 25},
    {device_id: 'node-02', timestamp: '2026-10-17T12:00:00Z', temperature_c: 29},
  ];
  const before = JSON.stringify(rows);
  const grouped = groupEnvironmentReadings(rows, ts => new Date(ts));
  assert.equal(grouped.size, 2);
  assert.equal(grouped.get('node-01').length, 2);
  assert.equal(grouped.get('node-01')[0].probe_id, 1);
  assert.equal(grouped.get('node-01')[1].probe_id, 2); // Does not depend on Probe 1 being online.
  assert.equal(grouped.get('node-02')[0].temperature_c, 29);
  assert.equal(groupReadings(rows, ts => new Date(ts)).size, 5);
  assert.equal(JSON.stringify(rows), before);
});

test('environmental selection is deterministic and normalizes equivalent timestamps', async () => {
  const { groupEnvironmentReadings } = await import('../src/probeIdentity.js');
  const rows = [
    {device_id: 'node-01', probe_id: 2, id: 10, timestamp: '2026-10-17T12:00:00Z'},
    {device_id: 'node-01', probe_id: 1, id: 9, timestamp: '2026-10-17T07:00:00-05:00'},
    {device_id: 'node-01', probe_id: 1, id: 11, timestamp: '2026-10-17T12:00:00Z'},
    {device_id: 'node-01', probe_id: 1, timestamp: 'invalid'},
  ];
  for (const input of [rows, [...rows].reverse()]) {
    const readings = groupEnvironmentReadings(input, ts => new Date(ts)).get('node-01');
    assert.equal(readings.length, 1);
    assert.equal(readings[0].id, 11);
  }
});
