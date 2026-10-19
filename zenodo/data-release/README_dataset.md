# Conformome pilot release v0.1.0: data

An index of experimental and computational evidence on the conformational states of proteins, RNA and DNA.
- Website: https://conformome.org
- Source code: https://github.com/matth55/conformome, archived at doi:10.5281/zenodo.SOFTWARE_VERSION_DOI

Cite as: Halma MTJ. Conformome pilot release v0.1.0: conformational-state evidence records for proteins and nucleic acids. Zenodo; 2026. doi:10.5281/zenodo.DATA_VERSION_DOI

## Contents

The release covers 81 proteins and six nucleic acids:
- the adenine riboswitch aptamer (*V. vulnificus add*);
- the preQ1 class-I riboswitch (*B. subtilis*);
- HIV-1 TAR;
- the *Tetrahymena* group I intron P4–P6 domain;
- the SARS-CoV-2 frameshifting element;
- the human telomeric G-quadruplex (DNA).

Release totals: [fill in from `stats.json` of the release build]
- molecules: [n] (81 proteins, [n] RNA, [n] DNA)
- evidence entries: [n] (proteins [n], nucleic acids [n])
- techniques with entries: [n]
- curated molecules: [n]; states: [n] (nucleic-acid states: [n])

## Files

| File | Contents |
| --- | --- |
| `all-records.jsonl` | Every record, one JSON object per line. `record_type` is `molecule`, `state`, `transition`, `evidence` or `model`. A deprecated `protein` alias is kept for protein records in this release. |
| `molecules.zip` | One JSON bundle per molecule (`<molecule_id>.json`) |
| `profiles.zip` | Per-nucleotide reactivity profiles for chemical-probing evidence (`<evidence_id>.json`), referenced from each evidence record's `data_ref` |
| `schemas.zip` | JSON Schemas (v2.0.0) for every record type and their shared definitions |
| `techniques.yaml` | Technique taxonomy, including SHAPE, DMS, crosslinking-ligation sequencing, smFRET and UV melting |
| `curation.zip` | Per-molecule curation files: states (with dot-bracket secondary structure and G-quadruplex topology for nucleic acids), curator assignments, mapping rules. Each file carries its curation status. |
| `manifest.json` | Raw inputs: URL, retrieval date, SHA-256 |
| `CHANGELOG.md` | Schema changes from 1.x (protein → molecule; ion conditions; nucleic-acid state fields) |
| `README.md` | This file |
| `LICENSE` | CC BY 4.0 |

## Identifiers

| Molecule | `molecule_id` scheme | Example |
| --- | --- | --- |
| Protein | `uniprot:<accession>` (canonical isoform) | `uniprot:P37840` |
| Natural RNA with an RNAcentral entry | `rnacentral:<URS id>`, species-specific where available | `rnacentral:URS..._<taxid>` |
| Synthetic or unlisted sequence | `seq:<rna\|dna>:<first 8 hex of SHA-256 of the uppercase reference sequence>` | `seq:dna:3f9a1c2e` |

Each molecule record stores the full reference sequence. Evidence records store the construct sequence and its alignment to the reference (start, end, identity).

## Conditions

Evidence conditions include temperature, pH, environment, ligands, applied force and, from schema 2.0.0, ion concentrations (Mg²⁺, K⁺, Na⁺, Li⁺, in mM), ionic strength and denaturant. Unreported values are `null`. Two measurements are compared for conflicts only if their temperature, pH, environment, ligands, monovalent cation species and denaturant match, and their [Mg²⁺] values agree within a factor of 2. Reactivity profiles and force observables are not compared.

## Licence and source attribution

The Conformome records, curation files, schemas and taxonomy are released under CC BY 4.0. Evidence records derive from the sources below, whose terms continue to apply to the underlying data.

| Source | Used for | Terms |
| --- | --- | --- |
| RCSB PDB / wwPDB | protein and nucleic-acid structures | CC0 1.0 |
| AlphaFold DB (EMBL-EBI / Google DeepMind) | protein models | CC BY 4.0, attribution required |
| DisProt | protein disorder annotations | CC BY 4.0 |
| BMRB | NMR data | [confirm] |
| SASBDB | scattering data | [confirm] |
| RNA Mapping Database (RMDB) | chemical-probing reactivity profiles | [confirm] |
| RNAcentral | RNA identifiers and cross-references only, no evidence | CC0 1.0 [confirm] |
| MDDB | simulations | varies by project; see each record's `provenance.licence` |
| SMASH-BIO | force spectroscopy | [confirm; leave out of this archive if not redistributable] |

Records whose source licence does not permit redistribution are not included here; the website links them at source. Leave out any reactivity profile whose RMDB licence is unconfirmed until it is confirmed.

## Funding

This project has received funding from the European Union's Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No 859853 (AntiHelix).
