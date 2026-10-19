# Curation

One YAML file per pilot protein, named by UniProt accession (`P69441.yaml`). The curator owns these files; the pipeline reads them and never edits them.

Fields:

- `uniprot`, `name`, `curator`: identity and who is responsible for the content.
- `status`: `draft` until a curator has reviewed it; the site labels draft pages.
- `as_of`: the date the file was last changed. Used as the retrieval date of the curation's provenance.
- `states`: `id`, `name`, `basis` (observed or inferred), `representative_pdb` (observed states export it), `description`, `assumptions` (required for inferred states), optional `parent`.
- `assignments`: each names an `evidence_id` (for example `EV-PDB-4AKE-1`) or a `pdb` ID (every entity of this protein in that entry), a `state`, a `confidence` (high, medium or low) and a one-line `justification`. Each becomes a mapping record with `who: curator:<curator>`.
- `rules`: each has an `id`, a `state`, a `confidence`, a one-line `justification` and `match` criteria, all of which must hold: `techniques`, `sources`, `observable_types`, `environment`, `ligands_any`, `ligands_all`, `ligands_none`, `no_ligands`, `ligand_text_any`, `ligand_text_none` (substring of the ligand list, which includes `branched: <oligosaccharide>` and `partner: <molecule>` entries), `title_any`, `title_all`, `title_none` (title plus construct text) and `publication_title_any` (title only). Each match becomes a mapping record with `who: rule:<id>`. Curator assignments win over rules; items matched by rules for different states stay unmapped and are listed as ambiguous.
- `transitions`: empty in the pilot. A transition needs its own provenance and evidence IDs; see `schema/transition.schema.json`.

Run `make map` after editing, then `make validate`.
