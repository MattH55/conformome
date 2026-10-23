# Open Research Europe submission notes

Updated 2026-10-23. The field-by-field answers for the form are in `paper/submission/form_answers.md`; this file keeps the author's decisions that the form answers are built from.

## Article

- **Article type:** Software Tool Article
- **Subject:** Biological sciences › Structural biology / Biophysics
- **Title:** Conformome: an index of experimental evidence on the conformational states of proteins and nucleic acids, mapped across techniques
- **Author:** Matthew T. J. Halma, Open Source Medicine, Tallinn, Estonia. ORCID: \[to be filled\]
- **Keywords (8):** protein conformation; conformational ensembles; structural biology; FAIR data; database; integrative structural biology; single-molecule biophysics; RNA structure

## Eligibility

Horizon 2020 MSCA ITN AntiHelix, grant agreement 859853 (project ended; ORE accepts results of completed H2020 projects). Conformome extends the conformational-ensemble and FAIR-data work of that fellowship; it ingests SMASH-BIO and builds on the Table 3 standard, both outputs of the same project.

*Confirm with ORE if in doubt.*

## Competing interests

M.T.J.H. is a former employee of LUMICKS B.V., a manufacturer of optical tweezers instruments, and develops SMASH-BIO, one of the sources ingested by Conformome. No other competing interests were disclosed.

## AI-use disclosure

Paste this into the submission form, verbatim from the Acknowledgements (fill the model version first, in both places):

> The author used Claude (Anthropic; \[to be filled: model version\]) to help draft and edit the manuscript text and to write parts of the pipeline, website and figure code, in order to speed up writing and software development. The author checked all content, numbers and interpretations and takes full responsibility for them. No generative AI was used to create or alter figures.

## Upload set

Everything is in `paper/submission/`:

- `Conformome_ORE_manuscript.docx` (the file ORE takes; the `.pdf` is a reading copy)
- `figures/Figure1.tiff` … `figures/Figure4.tiff` (PNG copies alongside)
- Data availability DOI and software availability DOI, once the `v0.1.0` GitHub release has been archived by the GitHub–Zenodo integration and the data archive has been published. Do not mint a DOI another way. Steps: `release_meta/DEPOSIT.md`.

## Suggested reviewers

Every affiliation is marked *confirm*. No email addresses. The author should prune this list.

| Name | Affiliation (*confirm*) | Expertise | Why |
| --- | --- | --- | --- |
| Kresten Lindorff-Larsen | Linderstrøm-Lang Centre for Protein Science, University of Copenhagen (*confirm*) | Ensembles, molecular dynamics and integrative modelling | Works on conformational ensembles and the comparison of simulations with experiment |
| Benjamin Schuler | Department of Biochemistry, University of Zurich (*confirm*) | Single-molecule FRET of disordered proteins | Measures conformational dynamics of disordered proteins, a gap in the pilot |
| Andrej Šali | Department of Bioengineering and Therapeutic Sciences, University of California, San Francisco (*confirm*) | Integrative structures, PDB-IHM | Leads integrative modelling and the PDB-IHM archive that Conformome points to |
| Mihaly Varadi | European Molecular Biology Laboratory, European Bioinformatics Institute (*confirm*) | PDBe-KB, AlphaFold DB, data integration | Maintains PDBe-KB and AlphaFold DB, both discussed as neighbouring resources |
| Michael Woodside | Department of Physics, University of Alberta (*confirm*) | Force spectroscopy of folding | Experimental single-molecule force spectroscopy of protein folding |
| Lewis Kay | Departments of Molecular Genetics, Biochemistry and Chemistry, University of Toronto (*confirm*) | NMR of excited states | NMR methods for sparsely populated conformational states |
| Silvio Tosatto | Department of Biomedical Sciences, University of Padua (*confirm*) | DisProt and PED | Closest existing resources. Conformome links to DisProt and PED rather than duplicating them |

## Exclude

- VU Amsterdam (Wuite, Peterman and Heller groups)
- Co-authors of Halma et al. 2025: Kumar, van Eck, Abeln, Gates
- Current or former LUMICKS staff
