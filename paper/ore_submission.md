# Open Research Europe submission notes

## Article

- **Article type:** Software Tool Article
- **Subject:** Biological sciences › Structural biology / Biophysics
- **Title:** Conformome: a per-protein index of experimental evidence on conformational states, mapped across techniques
- **Author:** Matthew T. J. Halma, Open Source Medicine, Tallinn, Estonia
- **Keywords:** protein conformation; conformational ensembles; structural biology; FAIR data; database; integrative structural biology; single-molecule biophysics; data integration

## Eligibility

Horizon 2020 MSCA ITN AntiHelix, grant agreement 859853 (project ended; ORE accepts results of completed H2020 projects). Conformome extends the conformational-ensemble and FAIR-data work of that fellowship; it ingests SMASH-BIO and builds on the Table 3 standard, both outputs of the same project.

*Confirm with ore@f1000.com if in doubt.*

## Competing interests

M.T.J.H. is a former employee of LUMICKS B.V., an optical tweezers manufacturer. M.T.J.H. also develops SMASH-BIO, one of the sources Conformome ingests.

## AI-use disclosure

Paste this into the submission form, verbatim from the Acknowledgements:

> The author used Claude (Anthropic) to draft and edit the manuscript text and to write parts of the pipeline, site-generation and figure code. All content, numbers and interpretations were checked by the author, who takes full responsibility for them; the AI tool is not an author.

## Upload set

- `paper/out/manuscript.docx`
- `paper/figures/fig1_model.tiff`
- `paper/figures/fig2_coverage.tiff`
- `paper/figures/fig3_screens.tiff`
- `paper/figures/fig4_pipeline.tiff`
- Data availability DOI and software availability DOI, once the GitHub–Zenodo integration has archived the `v0.1.0-paper` tag. Do not mint a DOI another way. See the pull request for the steps if the integration is not enabled.

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
