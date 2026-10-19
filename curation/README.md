# Curation

One YAML file per pilot protein, named by UniProt accession (`P69441.yaml`). The curator owns these files; the pipeline reads them and never edits them.

Fields:

- `uniprot`, `name`, `curator`: identity and who is responsible for the content.
- `status`: `draft` until a curator has reviewed it; the site labels draft pages.
- `as_of`: the date the file was last changed. Used as the retrieval date of the curation's provenance.
- `states`: `id`, `name`, `basis` (observed or inferred), `representative_pdb` (observed states export it), `description`, `assumptions` (required for inferred states), optional `parent`.
- `assignments`: each names an `evidence_id` (for example `EV-PDB-4AKE-1`), a `state`, a `confidence` (high, medium or low) and a one-line `justification`. Each becomes a mapping record with `who: curator:<curator>`.
- `transitions`: empty in the pilot. A transition needs its own provenance and evidence IDs; see `schema/transition.schema.json`.

Run `make map` after editing, then `make validate`.
