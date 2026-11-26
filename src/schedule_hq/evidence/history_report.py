"""Generate a deliberately redacted static report, never publish private history."""
import html
from schedule_hq.evidence.public import public_summary
from schedule_hq.history.events import validate_event

def render(events):
    rows=[]
    for e in events:
        validate_event(e)
        r=public_summary(e["receipt"])
        # Source provenance is a recorded assertion, not a verified outcome.
        label={"synthetic":"synthetic","unverified":"unverified","authenticated":"recorded authenticated claim"}[e["provenance"]]
        # Never expose raw free text, links, private IDs or hashes.
        values=[r["task_id"],r["scheduled_at"],r["started_at"] or "Not observed",
                r["completed_at"] or "Not observed",r["classification"],label,
                str(len(e["receipt"]["positives"])),str(len(e["receipt"]["negatives"]))]
        rows.append(tuple(values))
    headings=("Task","Nominal UTC","Start UTC","End UTC","Reported outcome","Evidence scope","Positives (count)","Negatives (count)")
    head="".join('<th scope="col">'+html.escape(v)+'</th>' for v in headings)
    body="".join("<tr>"+"".join("<td>"+html.escape(v)+"</td>" for v in row)+"</tr>" for row in sorted(rows))
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Schedule HQ execution evidence</title><style>body{font:16px system-ui;color:#172033;background:#f5f7fa;margin:24px auto;padding:0 16px;max-width:1100px}'
            'table{border-collapse:collapse;width:100%;background:white}th,td{text-align:left;padding:10px;border-bottom:1px solid #bfc9d4}'
            'caption{text-align:left;font-weight:bold;padding:8px}.table-wrap{overflow-x:auto}.table-wrap:focus{outline:2px solid #175ab0}p{max-width:75ch}</style>'
            '<main><h1>Schedule HQ execution evidence</h1><p>Sanitized offline observation report. No live delivery, authority, or proof authenticity is asserted. Missing records are not success.</p>'
            '<div class="table-wrap" tabindex="0" role="region" aria-label="Execution observations"><table><caption>Recorded observations (UTC)</caption>'
            '<thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'
            '<p>'+str(len(rows))+' observations. Free text and private identifiers are omitted.</p></main></html>\n')
