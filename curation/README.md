# Curation

One YAML file per molecule, named by its molecule ID (`P69441.yaml`; RNA, DNA and complex IDs are described in `docs/METHODS.md`). The curator owns these files; the pipeline reads them and never edits them.

Fields:

- `uniprot` (proteins) or `molecule_id` (any molecule), `name`, `curator`: identity and who is responsible for the content.
- `status`: `draft` until a curator has reviewed it; the site labels draft pages.
- `as_of`: the date the file was last changed. Used as the retrieval date of the curation's provenance.
- `states`: `id`, `name`, `basis` (observed or inferred), `representative_pdb` (observed states export it), `description`, `assumptions` (required for inferred states), optional `parent`, and optionally:
  - `family_label`: `{vocabulary: kinase, terms: {dfg: dfg_out, alpha_c: alpha_c_in}}`, terms from `taxonomy/state_vocabularies/<vocabulary>.yaml`.
  - `secondary_structure` (RNA and DNA only): `{dot_bracket: "(((...)))", source: "1Y26", start: 1}`.
  - `population`: `{value: 0.7, uncertainty: 0.05, method: DRACO clustering, evidence_ids: [EV-...]}`.
- `assignments`: each names an `evidence_id` (for example `EV-PDB-4AKE-1`) or a `pdb` ID (every entity of this protein in that entry), a `state`, a `confidence` (high, medium or low) and a one-line `justification`. Each becomes a mapping record with `who: curator:<curator>`.
- `rules`: each has an `id`, a `state`, a `confidence`, a one-line `justification` and `match` criteria, all of which must hold: `techniques`, `sources`, `observable_types`, `environment`, `ligands_any`, `ligands_all`, `ligands_none`, `no_ligands`, `ions_any`, `ions_none` (ion names as in conditions, for example `K+`, `Na+`, `Mg2+`), `ligand_text_any`, `ligand_text_none` (substring of the ligand list, which includes `branched: <oligosaccharide>` and `partner: <molecule>` entries), `title_any`, `title_all`, `title_none` (title plus construct text) and `publication_title_any` (title only). Each match becomes a mapping record with `who: rule:<id>`. Curator assignments win over rules; items matched by rules for different states stay unmapped and are listed as ambiguous.
- `transitions`: empty in the pilot. A transition needs its own provenance and evidence IDs; see `schema/transition.schema.json`.

Run `make map` after editing, then `make validate`.
