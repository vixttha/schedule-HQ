# Provenistem — Feature library

A feature is a durable identity for a **project-owned capability**, distinct from brainstorming and from release membership. The files in `records/` are canonical; `INDEX.md` is a derived view and begins empty.

Create `records/FEAT-000001.json` from `../templates/feature.example.json`, give it a new ID, and fill out actual facts. Preserve IDs through implementation changes, renames and versions.

`idea_ids` may refer to ideas in `../ideas/records/`. Features can also be proposed directly with no linked idea. Feature lifecycle, implementation, testing evidence and shipped version are deliberately different. `release_membership: NOT_ASSERTED` prevents this optional library from manufacturing publication truth.

See [schema v1](schema/v1/feature.schema.json), [lifecycle rules](../docs/LIFECYCLE.md), and [isolation](../docs/ISOLATION.md).
