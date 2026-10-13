import csv,json,html
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Build the readable report from an export and generated JSON reports.')
parser.add_argument('csv')
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
comparison=json.loads((root/'reports/watering_comparison.json').read_text())
summary=json.loads((root/'reports/sensor_intelligence_summary.json').read_text())
central=ZoneInfo('America/Chicago')
rows=list(csv.DictReader(open(args.csv)))
def stamp(row):return datetime.fromisoformat(row['timestamp']).replace(tzinfo=timezone.utc)
def chart(data,target,key,label,maximum):
 lo=target-timedelta(hours=1);hi=target+timedelta(hours=2)
 data=sorted([r for r in data if lo<=stamp(r)<=hi],key=stamp)
 x=lambda t:60+(t-lo).total_seconds()/10800*790
 y=lambda v:160-float(v)/maximum*120
 parts=[f'<svg viewBox="0 0 900 205" role="img" aria-label="{label}"><title>{label}</title>']
 for v in [0,maximum/2,maximum]:
  parts.append(f'<path d="M60 {y(v)}H850" stroke="#dce5e7"/><text x="48" y="{y(v)+4}" text-anchor="end">{v:g}</text>')
 prev=None
 for r in data:
  t=stamp(r);xx=x(t);yy=y(r[key]);tip=html.escape(t.astimezone(central).strftime('%b %d %I:%M:%S %p CDT')+' • '+r[key]+' = '+r[key]+' • record '+r['id'])
  if prev and (t-prev[0]).total_seconds()<=900:
   parts.append(f'<path d="M{prev[1]:.2f} {prev[2]:.2f}L{xx:.2f} {yy:.2f}" stroke="#137c78" stroke-width="2" fill="none"/>')
  parts.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="3" fill="#137c78"><title>{tip}</title></circle>')
  prev=(t,xx,yy)
 parts.append(f'<path d="M{x(target)} 25V165" stroke="#d17132" stroke-width="2" stroke-dasharray="5 4"/>')
 for hour in range(4):
  t=lo+timedelta(hours=hour)
  parts.append(f'<text x="{x(t)}" y="190" text-anchor="middle">{t.astimezone(central).strftime("%I:%M %p")}</text>')
 parts.append('</svg>')
 return '<h4>'+label+'</h4>'+''.join(parts)
notes=[('Visible response; automatic detection skipped','The readings changed from 0% to 89.9% within 29 seconds after your reported time. By 4:07 p.m., they were at 91.8%. The detector skipped this event because node 02 was sending readings seconds apart during startup, rather than at its usual ten-minute cadence. An earlier brief rise also returned to 0%, so this period needs careful interpretation.'),('Possible watering detected','Raw readings fell from 2,981 to 1,072 at your reported timestamp, then stayed low. The display reached 100%. The detector now recognizes this sustained response even though the percentage is clipped.'),('Possible watering detected','Raw readings fell from 2,813 to 1,008 between 3:37:49 and 3:47:52 p.m. Central. The display reached 100% and stayed there in the following readings. This is near your approximate 4 p.m. watering time; the sensor observation does not establish the exact moment you watered.')]
body='''<header><div class="eyebrow">BACKYARDOS · EXPERIMENTAL SENSOR INTELLIGENCE</div><h1>What your watering tests tell us</h1><p class="lead">The sensor shows a wetter response around all three watering events you reported for node 02. The software now identifies two of them automatically. The first remains a manual review because it happened during setup.</p><p>Prepared October 13, 2026 · Historical CSV only · All chart times are Central Daylight Time</p></header>
<section class="intro"><h2>Why we’re doing this</h2><p>Before BackyardOS can give useful alerts or forecasts, it needs to distinguish a lasting moisture change from a bad reading. Your watering notes give us real events to compare with the sensor. This report explains that comparison; you do not need to read the JSON files.</p><div class="tiles"><div><strong>3</strong>watering events you reported</div><div><strong>2</strong>nearby automatic candidates</div><div><strong>0</strong>changes to your running system</div></div></section>
<section><h2>How to read the charts</h2><p>The green dots are actual readings. The orange dashed line marks your reported watering time. Hover over a dot for its exact time, value and record number. Lines connect readings only when they are no more than 15 minutes apart; gaps are left open.</p><p><b>Displayed moisture:</b> 100% means the reading reached the calibration’s wet limit. It does not measure physical saturation. <b>Raw sensor reading:</b> a lower number means a wetter response. Raw values can keep changing even when the display stays at 100%.</p></section>'''
node2=[r for r in rows if r['device_id']=='backyard-node-02']
for i,e in enumerate(comparison['comparisons']):
 label=e['user_report'];t=datetime.fromisoformat(label['reported_time_utc']);title,note=notes[i]
 body+=f'<section><div class="eyebrow">NODE 02 · WATERING {i+1}</div><h2>{t.astimezone(central).strftime("%B %d · %-I:%M %p Central")}</h2><span class="badge">{title}</span><p>{note}</p><p class="small">Your reported time: {t.isoformat()} UTC offset included. {html.escape(label["precision"])}.</p>'
 body+=chart(node2,t,'soil_moisture_pct','Displayed moisture (%)',100)+chart(node2,t,'soil_moisture_raw','Raw sensor reading — lower means wetter',4095)+'</section>'
body+='<section><h2>Why a result may be withheld</h2><p>“Withheld” means the software saw a moisture rise but could not safely label it as possible watering. It does not mean you did not water.</p><ul><li><b>Readings too close together:</b> several quick samples cannot substitute for a lasting response. This explains the August 28 result.</li><li><b>Not enough before or after readings:</b> we cannot establish a starting point or persistence.</li><li><b>Gap, duplicate or sensor warning:</b> the evidence is unreliable.</li><li><b>Starting readings contain an abrupt change:</b> recovery from a dry-looking glitch can mimic watering.</li><li><b>Response fades or raw values disagree:</b> the change is too brief or inconsistent.</li></ul></section>'
node1=[r for r in rows if r['device_id']=='backyard-node-01']
for event_time,title,description in [
 ('2026-08-22T14:39:17+00:00','Node 01 · August 22, around 9:39 a.m.','Still an unconfirmed possible event. Displayed moisture rose from about 62% to 89% and stayed above 86% for the next two readings. Environmental readings in that five-reading window do not trigger the current fault checks. However, the preceding hour contains an outage and another sharp moisture change. This limits interpretation; the data cannot establish whether water was added or the probe was handled.'),
 ('2026-08-22T23:51:31+00:00','Node 01 · August 22, around 6:51 p.m.','Automatic result now withheld. The probe was reading about 85%, suddenly fell to 0% for two readings, then returned to 84–97%. Calling that recovery watering would be misleading. The new safeguard rejects a starting baseline that contains this abrupt change. The cause remains unknown; this is not proof of hardware failure.')]:
 t=datetime.fromisoformat(event_time)
 body+='<section><div class="eyebrow">REVIEW OF OLDER READINGS</div><h2>'+title+'</h2><p>'+description+'</p>'+chart(node1,t,'soil_moisture_pct','Displayed moisture (%)',100)+'</section>'
body+='''<section><h2>What changed in the experiment</h2><p>The first version rejected any event containing 0% or 100% readings. That was too restrictive for your September and October watering. It now allows those readings when the raw sensor shows a lasting wetting response. It retains warnings for large changes, because probe movement or hardware changes can look similar.</p><p>The updated scan retains three possible events overall: two on node 02 near your reports and one on node 01 on August 22. Another node 01 result is now withheld because its baseline follows a sudden dry-looking jump. The remaining node 01 result is unconfirmed; see the review below. Allowing large changes can increase false alarms, so none is labeled confirmed watering.</p><p>Fourteen automated tests pass. They check that brief spikes, flat 100% readings, frozen raw values, duplicate records, fast sampling and a false dry dip do not produce watering candidates. They also check that a sustained clipped response can remain a low-confidence candidate, and that invalid readings and gaps block results. These checks show that the rules behave as designed. They do not establish real-world accuracy; these three reported events were used to improve the rules.</p></section>
<section class="pending"><h2>Today’s node 01 test is still pending</h2><p>You reported adding water around <b>2:10 p.m. Central on October 13</b> (19:10 UTC, approximate). The CSV ends earlier that day: node 01’s final reading is at 11:30:58 a.m. Central. It cannot show this new watering yet.</p><p>When a new export is available, we can compare the next several readings with this reported time. Your expected 80–100% is a prediction to check, not a result we have observed.</p></section>
<footer><h2>Where this leaves us</h2><p>No extra watering is needed. The next useful check is today’s node 01 response, followed by a review of the unconfirmed August events. Everything remains local and experimental; your dashboard, Advisor and database have not changed.</p><p class="small">Source: sensorreading_rows.csv · 13,752 rows · nodes 01 and 02 analyzed independently · six node 03 test rows excluded. UTC storage confirmed by you; display uses America/Chicago. Source SHA-256: '''+summary['source_sha256']+'''</p></footer>'''
css='''body{margin:0;background:#edf3f3;color:#173438;font:17px/1.65 system-ui,sans-serif}main{max-width:980px;margin:auto;padding:40px 24px}header{padding:36px 0}h1{font-size:44px;line-height:1.12;max-width:740px;margin:18px 0}h2{font-size:27px;line-height:1.3}h4{margin-bottom:0}.eyebrow{font-size:12px;letter-spacing:2px;font-weight:750;color:#39716f}.lead{font-size:22px}section,footer{background:white;border:1px solid #dce6e6;border-radius:16px;padding:28px 34px;margin:24px 0}.small{font-size:13px;color:#536c71;overflow-wrap:anywhere}.tiles{display:flex;gap:20px}.tiles div{flex:1;background:#edf6f4;padding:18px;border-radius:10px}.tiles strong{display:block;font-size:36px;color:#137c78}.badge{display:inline-block;background:#edf6f4;color:#24605c;padding:6px 12px;border-radius:8px;font-size:14px;font-weight:650}svg{width:100%;height:auto}svg text{font:13px system-ui;fill:#51696c}.pending{border-left:5px solid #d17132}@media(max-width:600px){h1{font-size:34px}section,footer{padding:20px}.tiles{display:block}.tiles div{margin:10px 0}}@media print{body{background:white}main{padding:0}section{break-inside:avoid}header{padding:0}section,footer{border-radius:0}}'''
followup_path=root/'reports/node01_oct13_assisted.json'
if followup_path.exists():
 followup=json.loads(followup_path.read_text())
 found=bool(followup.get('assisted_candidates'))
 section_start=body.index('<section class="pending">')
 section_end=body.index('</section>',section_start)+len('</section>')
 followup_section='<section class="pending"><h2>Today’s node 01: possible watering, with a disturbance warning</h2><p>The screenshot shows 0% at 2:06 p.m. Central, followed by 99.6% at 2:16 p.m. and 99.2–100% through 3:36 p.m. This is consistent with your approximately 2:10 p.m. watering.</p><p>Record 13812 at 2:01 p.m., with pressure 610.21 hPa, is excluded from event evidence because you identified it as a disturbance while moving things around. It remains preserved in the audit.</p><p><b>Assisted result:</b> '+('possible watering, with a disturbance warning.' if found else 'no qualifying result.')+' This uses your explicit exclusion, three steady baseline readings and three sustained later readings. The unassisted detector still withholds a result. The watering time itself is not used to trigger detection.</p><p><b>Tradeoff:</b> this can recover useful evidence near a known disturbance, but probe handling can also cause a lasting moisture change. It remains low confidence and cannot confirm watering from sensor data alone. Long gaps and remaining hardware warnings are still blocked.</p><p>This follow-up uses 19 screenshot-transcribed readings, not a fresh database export. Historical charts still use the earlier CSV. All displayed times are Central Daylight Time.</p></section>'
 body=body[:section_start]+followup_section+body[section_end:]
 body=body.replace('Fourteen automated tests pass.', 'Twenty-one automated tests pass, including seven checks of the assisted exclusion path.')
 body=body.replace('The next useful check is today’s node 01 response, followed by a review of the unconfirmed August events.', 'The next useful check is a future watering event evaluated with these settings unchanged.')
(root/'reports/watering_report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>BackyardOS watering report</title><style>'+css+'</style><main>'+body+'</main></html>')
print('Created readable watering report.')
