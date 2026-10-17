# kit.json

The agent writes this file; `build_kit.py render` turns it into the briefing. Paths are relative to the kit folder. Every field is optional except `appliance`; missing pieces become Missing entries automatically.

```json
{
  "created": "YYYY-MM-DD",
  "appliance": {"brand": "GE", "type": "Dishwasher", "model": "GSD5560G00SS", "serial": "DF123456A", "name": "Triton GSD5560G00SS"},
  "summary": "Two or three plain sentences: what it is, how old, recall status, the one thing to know.",
  "label": {
    "location": "inside the door frame, left side",
    "photos": ["label/photo.jpg"],
    "fields": [{"field": "Model", "value": "GSD5560G00SS", "confidence": "high|low"}],
    "uncertain": ["The 7th serial character could be 8 or B."]
  },
  "age": "<serial_decode.py output> + \"summary\": one sentence with the reasoning",
  "recall": {"verdict": "covered|not covered|unclear|no recall found|check failed",
             "url": "https://www.cpsc.gov/...", "summary": "One or two plain sentences."},
  "manual": {"title": "...", "publication": "pub. number, date", "pdf": "manual/x.pdf",
             "markdown": "manual/manual.md", "url": "where it was downloaded from"},
  "care": [{
    "title": "Cleaning the filter",
    "guide": "diagrams/filter-guide.png",
    "intro": "What the parts are, in plain words.",
    "steps": [{"text": "...", "source": "Manual p. 11", "source_url": "optional https link"}],
    "when_to_call": "the condition only; it follows the words 'Stop and call for service if:'"
  }],
  "facts": [{"text": "Other useful fact.", "source": "Manual p. 5 or https://..."}],
  "links": [{"label": "Maker support page", "url": "https://..."}],
  "missing": [{"what": "Owner's manual (PDF)", "why": "...", "try": "the one thing to try"}]
}
```

Rules:
- `label.fields` lists exactly what the photo shows; nothing looked up goes there.
- Every `care` step has a `source`. `render` reports unsourced steps as errors.
- `missing.try` is one action the person can take, not a list.
