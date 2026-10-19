---
title: "Conformome: an index of experimental evidence on the conformational states of proteins and nucleic acids, mapped across techniques"
---

::: {custom-style="Author"}
Matthew T. J. Halma^1^ \[to be filled: ORCID iD\]

^1^ Open Source Medicine, Pärnu mnt. 139c, 11317 Tallinn, Estonia

Corresponding author: Matthew T. J. Halma (mhalma@opensourcemed.info)
:::

## Abstract

**Background.** The function of a protein or nucleic acid depends on the conformations it adopts, but the evidence on those conformations is divided by technique. Structures are deposited in the PDB, NMR data in the BMRB, scattering profiles in SASBDB and RNA chemical-probing data in the RNA Mapping Database, while simulations sit in molecular dynamics archives and force-spectroscopy results mostly in the literature. No existing resource brings this evidence together for one molecule and relates it to the states the molecule is thought to adopt.

**Methods.** Conformome (https://conformome.org) collects experimental and computational entries for each protein, RNA or DNA molecule from eight sources: the RCSB PDB, BMRB, SASBDB, the RNA Mapping Database, DisProt, MDDB, AlphaFold DB and SMASH-BIO. Each entry keeps its technique, construct, conditions (including ions), observable with uncertainty, and provenance. Curators define the states of each molecule and map entries to them individually or through explicit rules, and each mapping records who made it, with what confidence and why. States resolved directly by a structure are labelled observed; states fitted to indirect measurements are labelled inferred and must list their assumptions. Disagreements between comparable measurements are flagged rather than averaged.

**Results.** The pilot release covers 81 proteins and six nucleic acids, with \[to be filled: total\] evidence entries from \[to be filled: n\] techniques; \[to be filled: n\] molecules have draft curation, with \[to be filled: n\] states. Each molecule page shows a state-by-technique coverage grid that identifies states supported by a single method, together with the evidence, conflicts and structural models of observed states. All records, schemas and curation files can be downloaded.

**Conclusions.** Conformome makes the multi-technique evidence on the conformational states of proteins and nucleic acids findable and comparable, and shows where that evidence is sparse or inconsistent.

**Keywords:** protein conformation; conformational ensembles; structural biology; FAIR data; database; integrative structural biology; single-molecule biophysics; RNA structure

## Introduction

Most proteins interconvert between several conformations, and the populations and lifetimes of these conformations determine how the protein functions. Enzymes open and close around their substrates, receptors switch between inactive and active forms, and many proteins remain disordered until they bind a partner or assemble into fibrils[@henzlerwildmanDynamicPersonalitiesProteins2007; @wrightIntrinsicallyDisorderedProteins2015; @chitiProteinMisfoldingAmyloid2017]. Each experimental technique captures a different part of this behaviour. Crystallography and cryo-EM resolve individual states at atomic detail. NMR can detect sparsely populated excited states and measure the rates at which they exchange[@sekharNMRPavesWay2013], and small-angle scattering reports the overall dimensions of the ensemble[@kikhneyPracticalGuideSmall2015]. Single-molecule FRET and force spectroscopy follow individual molecules as they move between states[@lernerFRETbasedDynamicStructural2021; @bustamanteSinglemoleculeStudiesProtein2020], hydrogen--deuterium exchange identifies regions that transiently unfold[@massonRecommendationsPerformingInterpreting2019], and molecular dynamics simulations suggest pathways between states[@lindorfflarsenHowFastfoldingProteins2011]. The techniques overlap to some extent, but each typically provides information that the others do not.

Nucleic acids raise the same questions. Riboswitches change conformation when they bind a metabolite and in doing so regulate gene expression[@serganovDecadeRiboswitches2013]. Optical tweezers have mapped the folding landscapes of nucleic-acid hairpins and riboswitch aptamers, including intermediates that bulk methods do not resolve[@woodsideDirectMeasurementFull2006; @greenleafDirectObservationHierarchical2008], and G-quadruplexes adopt different strand topologies depending on their sequence and on the cations present[@burgeQuadruplexDNASequence2006]. Chemical probing with SHAPE or DMS reports which nucleotides are paired[@merinoRNAStructureAnalysis2005; @zubradtDMSMaPseqGenomewideTargeted2017], and these data are collected in the RNA Mapping Database[@corderoRNAMappingDataBase2012]. As for proteins, each technique describes part of the conformational behaviour, and the results are held in different places.

The data from these techniques are organised by technique rather than by molecule. Structures are held in the PDB[@bermanProteinDataBank2000; @burleyUpdatedResourcesExploring2025], NMR data in the BMRB[@hochBiologicalMagneticResonance2023] and scattering data in SASBDB[@kikhneySASBDBTowardsAutomatically2020]. Ensembles of disordered proteins are collected in PED[@ghafouriPED2024Improving2024] and DisProt[@aspromonteDisProt2024Improving2024], simulations in archives such as MDDB[@amaroNeedImplementFAIR2025], and force-spectroscopy studies are indexed by SMASH-BIO[@halmaSMASHBIOReleaseV12026]. Natural RNAs are identified through RNAcentral[@rnacentralconsortiumRNAcentral2021Secondary2021], whereas many nucleic acids studied biophysically are synthetic constructs with no database identifier at all. Each repository has its own identifiers, observables and conventions for recording conditions, and none relates its entries to those held elsewhere. PDBe-KB aggregates per-residue annotations for each protein, and CoDNaS and PDBFlex describe the conformational diversity among PDB entries[@pdbekbconsortiumPDBeKBCollaborativelyDefining2022; @monzonCoDNaS202016; @hrabePDBFlexExploringFlexibility2016]; all three are based on structures alone. Integrative modelling combines data from several techniques[@routPrinciplesIntegrativeStructural2019], and its results are archived in PDB-IHM[@vallatNewSystemArchiving2021], but each entry describes one system and the archive is not designed as an index across proteins.

As a result, anyone who wants to know what has been established about the conformations of a particular protein or RNA must search each resource separately, decide whether differently named states are in fact the same, and judge whether measurements made under different conditions can be compared. Disagreements between techniques, which are often informative, are easily missed.

Conformome is designed to address this. It collects entries from existing repositories, keeps each entry with its conditions and provenance, and maps the entries onto a small number of curated states for each molecule. The results are published as open, machine-readable records following the FAIR principles[@wilkinsonFAIRGuidingPrinciples2016]. Two rules govern the mapping. Every state is labelled as observed or inferred, and inferred states must state the assumptions on which they rest. Where comparable measurements disagree, the disagreement is flagged and the values are not averaged. This article describes the design of the resource, its pilot release of 81 proteins and six nucleic acids, and the uses for which it is intended.

## Methods

### Implementation

**Data model.** Conformome uses five core record types, each defined by a JSON Schema (Fig. 1). A *molecule* record describes a protein, RNA or DNA and carries its reference sequence. Proteins are keyed on the UniProt accession of the canonical isoform[@uniprotconsortiumUniProtUniversalProtein2025], natural RNAs on their RNAcentral identifier[@rnacentralconsortiumRNAcentral2021Secondary2021], and synthetic sequences, such as DNA oligonucleotides, on a checksum of the reference sequence. A *state* record names a conformational state of that molecule, gives its parent where states are nested, and records its basis as observed or inferred. States of nucleic acids may also give a secondary structure in dot-bracket notation and, for G-quadruplexes, a strand topology. An *evidence* record describes one experimental or computational entry: its technique, the construct studied and its alignment to the reference sequence, the conditions (environment, temperature, pH, ligands, ion concentrations, denaturant and applied force), the observable with its value, uncertainty and unit, its provenance (source, DOI, deposit identifier, retrieval date and licence) and a link to the data. Conditions that are not reported are stored as null rather than omitted, and temperatures and concentrations are converted to common units. A *transition* record holds a rate or free-energy difference between two states, with its conditions and supporting evidence, and a *model* record holds the coordinates exported for a state. A further *mapping* record links an evidence item to a state and stores who made the link, a confidence level (high, medium or low) and a one-line justification.

**Techniques.** Each entry is assigned a technique from a published taxonomy (`techniques.yaml`) of \[to be filled: n\] techniques, \[to be filled: n\] of which have entries in the pilot release: X-ray crystallography, cryo-EM, microED, neutron diffraction, NMR structure, NMR dynamics, NMR chemical shifts, small-angle X-ray and neutron scattering, EPR/DEER, circular dichroism, FTIR and Raman spectroscopy, fluorescence, ensemble FRET, force spectroscopy, analytical ultracentrifugation, gel electrophoresis, integrative models, AlphaFold predictions[@jumperHighlyAccurateProtein2021] and molecular dynamics, together with the nucleic-acid techniques of SHAPE and DMS chemical probing, crosslinking-ligation sequencing, single-molecule FRET and UV melting. \[to be filled: check this list against the techniques with entries in the rebuilt release\] For each technique, the taxonomy records whether it resolves a state directly or constrains it indirectly.

**Observed and inferred states.** A state is labelled *observed* if it has been resolved directly by X-ray crystallography, cryo-EM, microED, neutron diffraction or NMR structure determination; an observed state must cite a representative PDB entry. A state is labelled *inferred* if it rests on measurements that average over the ensemble or report structure only indirectly, such as SAXS, CD, NMR dynamics, FRET, force spectroscopy and integrative models. An inferred state must list its assumptions, and the pipeline will not build one that does not. AlphaFold models and molecular dynamics simulations are, in addition, labelled as predictions. The same rules apply to nucleic acids: a state is observed only if a deposited structure resolves it, and a secondary structure derived from chemical probing is inferred, with the folding model and the restraints used listed among its assumptions. Chemical-probing data are stored as per-nucleotide reactivity profiles; their agreement with each curated secondary structure is reported as a score on the mapping record but is not used to make mappings.

**Sources.** Eight sources are ingested in the pilot release (Table 1): the RCSB PDB[@bermanProteinDataBank2000; @burleyUpdatedResourcesExploring2025], BMRB[@hochBiologicalMagneticResonance2023], the RNA Mapping Database (RMDB)[@corderoRNAMappingDataBase2012], AlphaFold DB[@varadiAlphaFoldProteinStructure2024], SMASH-BIO[@halmaSMASHBIOReleaseV12026], DisProt[@aspromonteDisProt2024Improving2024], MDDB[@amaroNeedImplementFAIR2025] and SASBDB[@kikhneySASBDBTowardsAutomatically2020]. SMASH-BIO records follow the FAIR reporting standard for optical tweezers experiments[@halmaFAIRDataOptical2025]. Each source module queries its source by molecule identifier or, for nucleic acids without one, by sequence, retains the source's own identifiers and licence terms, and writes evidence records. Evidence from sources whose licence does not allow redistribution is displayed and linked, but is not included in the downloads.

```{=latex}
\needspace{16\baselineskip}
```

| Source | Unit of evidence | Proteins / nucleic acids | Licence |
|:----------------|:-------------------------------------------------|-------------:|:--------------------|
| RCSB PDB | One item per polymer entity mapped to the accession, including integrative and SAXS models | 81 / \[n\] | CC0 1.0 |
| BMRB | One item per mapped entry | 79 / \[n\] | \[to be confirmed\] |
| AlphaFold DB | One item per model, with mean pLDDT | 76 / -- | CC BY 4.0 |
| SMASH-BIO | One item per extracted force result, or one item per study | 69 / \[n\] | \[to be confirmed\]; not redistributed |
| DisProt | One item per curated region with a structural term | 36 / -- | CC BY 4.0 |
| MDDB | One item per simulation project | 32 / \[n\] | Varies by project |
| RMDB | One item per chemical-probing dataset (reactivity profile with conditions) | -- / \[n\] | \[to be confirmed\] |
| SASBDB | Radius of gyration with uncertainty | 30 / \[n\] | \[to be confirmed\] |

: **Table 1.** Sources ingested in the pilot release.

::: {custom-style="Table Note"}
*Proteins / nucleic acids*, number of the 81 pilot proteins and six pilot nucleic acids with at least one entry from the source; \[n\], to be filled from the rebuilt release.
:::

Modules for PED ensembles[@ghafouriPED2024Improving2024], PDB-IHM restraint tables[@vallatNewSystemArchiving2021], ATLAS simulations[@vandermeerscheATLASProteinFlexibility2024] and literature extraction from Europe PMC[@rosonovskiEuropePMC20232024] have been written as stubs, but these sources are not yet ingested.

**Mapping evidence to states.** The states of each protein are defined in a curation file, and evidence is mapped to them in one of two ways. A *curator assignment* links a named evidence item to a state and always takes precedence. A *curated rule* maps every item that meets all of its criteria, which may include the technique, source, observable type, environment, the presence or absence of ligands and words in the entry title; each rule carries its own confidence and justification. If rules for two different states match the same item, the item is left unmapped and listed as ambiguous. A third method, which maps structures by RMSD to an anchor structure for each state, has been implemented and tested but is not used in this release.

**Conflicts.** Two evidence items are flagged as conflicting only if they map to the same state, report the same observable in the same unit, were measured under comparable conditions (temperatures within 5 °C, pH within 0.5 units, the same environment, ligands, monovalent cation species and denaturant, and Mg^2+^ concentrations within a factor of two), both report an uncertainty, and differ by more than their combined uncertainty. Values are never averaged across a conflict. Items without an uncertainty are not compared, and their number is reported so that an absence of conflicts is not mistaken for agreement. Force observables are not yet compared, because the conditions schema does not record the loading rate, and reactivity profiles are not compared because they are vectors rather than single values.

**Coverage grid.** For each protein, the mapped evidence is counted by state and technique, and states supported by only one technique are marked.

**Reproducibility.** The pipeline has four stages (Fig. 2). `make ingest` converts raw downloads into evidence records, `make map` applies the curation files, `make models` exports coordinates, and `make site` generates the website and every number on it. A manifest records the URL, retrieval date and SHA-256 checksum of each raw input; the raw downloads themselves are not stored in the repository.

### Operation

Conformome is a static website (https://conformome.org) that is regenerated from the pipeline outputs at each release. It requires only a current web browser and has no login or registration. The 3D viewer (Mol\*)[@sehnalMolViewerModern2021] requires JavaScript; the rest of the site is plain HTML.

**Pages.** The home page shows the totals for the current release and the proteins with the most evidence. The *Molecules* page lists all proteins and nucleic acids in a molecule-by-technique matrix shaded by the number of entries (Fig. 3). Each molecule has its own page (for proteins, `/protein/<UniProt>/`). The top of the page gives the molecule's type, identifiers and reference sequence, its curation status and counts of evidence items, mapped items, states, techniques, sources and conflicts. The curated states follow, each with its basis, its parent state, its representative structure or list of assumptions, its secondary structure for nucleic acids, and the techniques that support it, together with the state-by-technique coverage grid. A 3D viewer shows the exported model of each observed state. The lower part of the page holds the curated transitions, an evidence table that can be filtered by technique, environment, ions, source and mapping status, the rules and assignments that produced the mappings with the number of items each one maps, the list of conflicts and links to the per-protein downloads. Molecules that have not yet been curated are shown with their evidence only and are labelled "states not yet curated". The site also has a search page and a page describing the methods.

**Downloads.** All records are available as a single JSON Lines file in which a `record_type` field identifies molecule, state, transition, evidence and model records. The downloads also include one JSON bundle per molecule, the per-nucleotide reactivity profiles, the JSON Schemas for each record type and their shared definitions, the technique taxonomy, and the manifest of raw inputs with retrieval dates and checksums.

**Running the pipeline.** The pipeline is written in Python 3, and a release is built with `make ingest`, `make map`, `make models` and `make site`. To add or revise a molecule, a curator edits its YAML curation file, which holds the states, curator assignments and rules, and rebuilds. The build validates every record against its schema and stops if an inferred state has no assumptions. Corrections and new curation can be contributed through the GitHub repository, as described in its CONTRIBUTING.md file.

## Results and use cases

### The pilot release

The 81 proteins in the pilot release were chosen because a wide range of conformational evidence is available for them. They comprise well-studied folding models (ubiquitin, protein G, lysozyme, barnase, chymotrypsin inhibitor 2, BPTI and staphylococcal nuclease); proteins that undergo large conformational changes (maltose- and ribose-binding proteins, Hsp90, calmodulin, dihydrofolate reductase, HRas, ABL1 kinase, the β2-adrenergic receptor and KcsA); mechanically active proteins studied by force spectroscopy (titin, talin, filamin, spectrin, von Willebrand factor, kinesin-1, dynein and several myosins); and disordered or aggregation-prone proteins (α-synuclein, tau, amyloid precursor protein, prion protein, TDP-43 and huntingtin). Together they have 17,522 evidence entries from 19 techniques (Fig. 3). Thirty proteins have draft curation, with 68 states in total \[to be filled: re-check\]; the other 51 are shown with their evidence and labelled as not yet curated. X-ray crystallography (8,679 entries on 78 proteins) and cryo-EM (4,110 entries on 51 proteins) account for nearly three-quarters of all entries, followed by force spectroscopy (2,588 entries on 69 proteins) and NMR chemical shifts (780 entries on 79 proteins). Fluorescence, ensemble FRET and analytical ultracentrifugation each have entries for only one protein, and EPR/DEER, FTIR/Raman spectroscopy and gel electrophoresis for two. \[to be filled: re-check these protein figures against the rebuilt release\]

The six nucleic acids were chosen because each has been studied by several techniques and adopts more than one conformation: the adenine-sensing riboswitch aptamer of *Vibrio vulnificus* and the class-I preQ1 riboswitch, which fold around their ligands[@serganovDecadeRiboswitches2013; @greenleafDirectObservationHierarchical2008]; the HIV-1 TAR RNA, whose sparsely populated excited states were characterised by NMR[@sekharNMRPavesWay2013]; the P4–P6 domain of the *Tetrahymena* group I intron, whose tertiary structure forms in the presence of Mg^2+^; the SARS-CoV-2 frameshifting element, for which several alternative structures have been proposed; and the human telomeric G-quadruplex, a DNA sequence whose topology depends on the cations present[@burgeQuadruplexDNASequence2006]. Together they have \[to be filled: n\] evidence entries from \[to be filled: n\] techniques, \[to be filled: n\] of them chemical-probing datasets from RMDB. All six have draft curation with \[to be filled: n\] states.

### Use case: α-synuclein

The page for α-synuclein (UniProt P37840; Fig. 4) has 346 evidence entries from six sources and 14 techniques. Of these, 262 are mapped to one of three curated states and 84 are unmapped. The disordered monomer is an inferred state supported by 48 entries from eight techniques: NMR chemical shifts and dynamics, SAXS, EPR/DEER, CD, FTIR/Raman spectroscopy, gel electrophoresis and an integrative model. Its listed assumptions are that no structure of the free monomer has been observed, in line with NMR evidence that the monomer remains disordered in mammalian cells[@theilletStructuralDisorderMonomeric2016]; that ensemble sources such as PED and smFRET studies are not yet ingested; and that the protein is unbound and monomeric. The micelle-bound helical state is observed, with PDB 1XQ8 as its representative structure[@ulmerStructureDynamicsMicellebound2005], and is supported by three entries from two techniques, both of them NMR. The fibril state is also observed, with PDB 6A6B as its representative structure[@liAmyloidFibrilStructure2018], and is supported by 211 entries from four techniques. The different fibril polymorphs, which share a common structural core but differ in how their protofilaments pack[@liCryoEMFulllengthsynuclein2018], are not yet distinguished.

Several features of the evidence are apparent on this page but would be difficult to see from the source repositories. The evidence is unevenly distributed: 211 of the 262 mapped entries concern the fibril, whereas the disordered monomer, the form most relevant to the protein's normal function, rests on a small number of ensemble measurements. The micelle-bound state is supported by NMR alone. Nineteen force-spectroscopy entries from SMASH-BIO have not been mapped to any state, which indicates where further curation is needed. The page lists 33 conflicts between comparable measurements, each linked to the two entries concerned. \[to be filled: describe one conflict in a sentence once curation is reviewed.\]

### Use case: the human telomeric G-quadruplex

The telomeric G-quadruplex shows why conditions are recorded with every entry. The same sequence folds into a parallel structure in crystals grown in the presence of K^+^, into an antiparallel basket in Na^+^ solution, and into hybrid forms in K^+^ solution[@burgeQuadruplexDNASequence2006]. Conformome curates these as separate states, each with its cation conditions, and the conflict detector never compares measurements made in different cations. The page shows \[to be filled: n\] entries mapped to \[to be filled: n\] states; \[to be filled: describe which states are observed and which are inferred, which techniques support each (e.g. NMR, X-ray, CD topology signatures, force spectroscopy), and whether any conflicts remain once cation conditions are matched\]. Without the cation field, structures of different topologies would appear to contradict one another.

### Use case: identifying states with limited evidence

Across the curated molecules, the coverage grid identifies the states that are supported by a single technique; in this release there are \[to be filled: n\] such states out of \[to be filled: n\]. \[to be filled: name two or three single-method states from the release, with their protein and technique.\] These states are candidates for further experiments. A state detected only by NMR relaxation dispersion[@sekharNMRPavesWay2013], for example, could be tested by smFRET[@lernerFRETbasedDynamicStructural2021] or HDX-MS[@massonRecommendationsPerformingInterpreting2019].

### Use case: input for integrative and predictive modelling

For each state, the per-molecule bundles collect the structures, ensemble measurements and simulations that bear on it, with their conditions and uncertainties. Integrative modellers currently assemble this information by hand[@routPrinciplesIntegrativeStructural2019], and the same kind of multi-technique data is needed to evaluate methods that aim to predict conformational ensembles rather than single structures[@laneProteinStructurePrediction2023].

## Discussion and conclusions

Conformome differs from existing resources in two respects: it organises evidence by molecule and by state rather than by technique, for proteins and nucleic acids alike, and it states explicitly what each state is based on. Structure archives record which structures have been determined for a molecule. Conformome is intended to show which conformations a molecule is known to adopt, what evidence supports each of them, and where that evidence is inconsistent. It links to the original sources rather than replacing them: SMASH-BIO for force spectroscopy, RMDB for chemical probing, and the PDB, BMRB, SASBDB, DisProt and MDDB for the other techniques.

The pilot release has several limitations, which are also stated on the site. The curation is a draft and has not been reviewed by a second curator. Only canonical isoforms are recorded, and proteins with identical sequences but different accessions, such as the calmodulin paralogues, are not grouped. PED ensembles, PDB-IHM restraints, ATLAS simulations and measurements reported only in the literature (smFRET, HDX-MS, and DEER and CD data without deposits) are not yet ingested, so the inferred states of disordered proteins in particular have limited support. No transitions have been curated, and no models are exported for inferred states. Force measurements are not checked for conflicts, because the schema does not yet record the loading rate. For nucleic acids, the pilot covers six molecules; reactivity profiles are scored against curated secondary structures but not checked for conflicts, and protein–nucleic acid complexes are recorded only as evidence on each partner, not as complexes with states of their own. The accuracy of the rule-based mapping has not yet been measured against independent curation. \[to be filled: if a second curator reviews the pilot before submission, report agreement here; otherwise delete this note.\]

Mapping evidence to states requires judgement. Deciding that a high-FRET population, a closed crystal form and a compact SAXS envelope all describe the same state is a matter of interpretation. Conformome therefore records, for every mapping, who made it, which rule was used, the confidence assigned and the reason, so that users can examine a mapping, disagree with it and see how the picture changes.

Several extensions are planned within the same design. These include ingesting the remaining sources; extending the nucleic-acid set, including transcriptome-wide probing data and crosslinking-ligation sequencing; recording protein–nucleic acid complexes as molecules with states of their own; adopting family-level state vocabularies, such as those of KLIFS for kinases[@kanevKLIFSOverhaulAfter2021] and GPCRdb for G protein-coupled receptors[@pandyszekeresGPCRdb2023Statespecific2023], so that states can be compared across homologous proteins; recording the effects of mutations on state equilibria, using ΔΔG values from thermodynamic databases[@nikamProThermDBThermodynamicDatabase2021; @xavierThermoMutDBThermodynamicDatabase2021], large-scale stability measurements[@tsuboyamaMegascaleExperimentalAnalysis2023] and deep mutational scans[@fowlerDeepMutationalScanning2014]; adding folding and conformational kinetics as transitions; and releasing a fixed benchmark, built from the curated evidence, for methods that predict conformational ensembles.

To our knowledge, Conformome is the first resource to index the evidence on the conformational states of proteins and nucleic acids across techniques and to report, for each state, how well that evidence supports it. Its usefulness will increase as more proteins are curated, and the curation is open, attributed and reproducible from the published files.

## Data availability

**Underlying data**

Zenodo: Conformome pilot release \[to be filled: version\]. \[to be filled: Zenodo DOI\]

This project contains the following underlying data:

- `all-records.jsonl` (every molecule, state, transition, evidence and model record)
- One JSON bundle per molecule
- Per-nucleotide reactivity profiles for chemical-probing entries
- The JSON Schemas for all record types
- `techniques.yaml` (technique taxonomy)
- The per-molecule curation files
- The manifest of raw inputs (URL, retrieval date and SHA-256 checksum)

The same files can be downloaded from https://conformome.org/downloads/. Evidence from sources whose licence does not allow redistribution is not included in the archive and is linked at source.

Data are available under the terms of the \[to be filled: licence, e.g. Creative Commons Attribution 4.0 International license (CC-BY 4.0)\].

## Software availability

- Software available from: https://conformome.org
- Source code available from: https://github.com/matth55/conformome
- Archived source code at time of publication: \[to be filled: Zenodo DOI of the tagged release\]
- License: \[to be filled: e.g. MIT License\]

## Competing interests

M.T.J.H. is a former employee of LUMICKS B.V., a manufacturer of optical tweezers instruments, and develops SMASH-BIO, one of the sources ingested by Conformome. No other competing interests were disclosed.

## Grant information

This project has received funding from the European Union's Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No 859853 (AntiHelix).

*The funders had no role in study design, data collection and analysis, decision to publish, or preparation of the manuscript.*

## Acknowledgements

The author used Claude (Anthropic; \[to be filled: model version\]) to help draft and edit the manuscript text and to write parts of the pipeline, website and figure code, in order to speed up writing and software development. The author checked all content, numbers and interpretations and takes full responsibility for them. No generative AI was used to create or alter figures.

## References

::: {#refs}
:::

## Figure legends

**Figure 1. The Conformome data model.** Evidence from eight sources is recorded for each protein, RNA or DNA molecule with its technique, construct, conditions, value with uncertainty, and provenance. An evidence item supports a state only through a mapping record, made by a curator or by a curated rule, which carries a confidence level and a justification. States are either observed, in which case they cite a representative structure, or inferred, in which case they list their assumptions; states may be nested. Transitions link two states, and models are exported for observed states. Comparable measurements on the same state that disagree are flagged as conflicts and are not averaged.

**Figure 2. The build pipeline.** Raw downloads from each source are recorded in the manifest and converted into evidence records (`make ingest`). Curator assignments and curated rules map the evidence to states, and conflicts are detected (`make map`). Coordinates are exported for observed states (`make models`), and the website and downloads are generated (`make site`). The counts shown are those of the release described here and are generated from the release files.

**Figure 3. Coverage of the pilot release.** Molecule-by-technique matrix for the 81 proteins and six nucleic acids. Cells are shaded by the number of evidence entries on a logarithmic scale. Rows are grouped by molecule type and curation status and ordered by total number of entries within each group; columns follow the order of `techniques.yaml`. The bar above each column gives the number of proteins with at least one entry for that technique.

**Figure 4. The α-synuclein page.** Screenshots of https://conformome.org/protein/P37840/ from the release described here. (**A**) The three curated states, with their basis and supporting techniques. (**B**) The state-by-technique coverage grid. (**C**) The 3D viewer showing the fibril model (PDB 6A6B).
