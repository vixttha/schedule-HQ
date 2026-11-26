# Provenistem — Ideas library

Human-readable exploration backed by schema-guided JSON records. The files in `records/` are canonical; `INDEX.md` is a derived view and begins empty.

Create `records/IDEA-000001.json` from `../templates/idea.example.json`, give it a new ID, and fill out actual facts. Reuse the same ID across title changes; never recycle it. Check [schema v1](schema/v1/idea.schema.json) and [lifecycle rules](../docs/LIFECYCLE.md).

Ideas can be captured without being approved, planned, tested or implemented. A decision-bearing status requires an actual decision record within the idea. External project decision authority is never replaced by this local metadata.

The optional validator checks structure and references; human/LLM reading requires no software.
