# Conformations: a schema for biomolecular conformations, and forward models from sequence

A state in Conformome is a name with a basis (observed or inferred) and the evidence mapped to it. That is
enough to index what has been measured, but not to compute with: a state carries no description of which parts of
the molecule are folded, which bases are paired, or what a force-extension curve should show when it unfolds.
This module adds that layer, so that measured single-molecule data, deposited structures and predictions from
sequence can be compared quantitatively, and so that the gap between them becomes data.

## 1. Record types

| Record | Schema | What it is |
| --- | --- | --- |
| conformation | `schema/conformation.schema.json` | A structural description of one conformation, at one or more levels: secondary structure, folded and unfolded segments, contacts (base pairs), coordinates, or a weighted ensemble. Realises a curated state (`state_id`) or stands alone (a prediction not yet matched). Derived quantities carry the method, parameters and assumptions that produced them. |
| segment | `schema/segment.schema.json` | One resolved level in a measurement, before anyone says what it is: a branch of a force-extension curve (constant contour length), a transition between branches, a FRET level, a dwell state. From a single trajectory or a summary over many. |
| assignment | `schema/assignment.schema.json` | A scored hypothesis that a segment is a given conformation, state or transition. Every candidate is kept with its score and rank, not only the winner. |
| prediction_run | `schema/prediction_run.schema.json` | One run of a predictive method on one molecule: method, version, parameters, sequence hash, and training-data cutoff. |
| evaluation | `schema/evaluation.schema.json` | A score of a prediction run against a curated reference, with `held_out` saying whether the reference was deposited after the method's training cutoff. |

The vocabulary maps onto the one used for state assignment in force spectroscopy: a **branch** (constant contour
length on a force-extension curve) is a `segment` of kind `force_branch`; a **state** is the curated `state`; a
**state conformation** is a `conformation` with `state_id` set.

Levels of description are independent. A riboswitch state can be described by its dot-bracket alone, a protein
state by its representative coordinates alone, an ensemble by weighted members. The quantity force spectroscopy
measures, the contour length released on unfolding, is derived from whichever level exists:

    ΔLc = n_structured × l_residue − d_ends

with l_residue given as an interval (0.36–0.40 nm per amino acid, 0.55–0.63 nm per nucleotide) and d_ends the
distance between the attachment points (from coordinates, or taken as 0 and flagged as an upper bound).

## 2. What the pipeline builds (`make conformations`, after `make models`)

`conformome/conformations/build.py` writes `build/<id>/conformations.json`:

* one conformation per curated secondary structure (nucleic acids);
* one conformation per exported representative structure, traced with gemmi (Cα, or P/C4'), with end-to-end
  distance, radius of gyration, observed and unobserved segments, and ΔLc;
* one segment per force-spectroscopy evidence record reporting a contour-length increment (SMASH-BIO);
* assignments of every segment to every conformation, scored by distance from the predicted ΔLc interval.

The last item is the classical way force data are assigned to structures. It is the baseline that any learned
assignment model must beat on the same records.

`conformome/conformations/predict.py` writes `build/<id>/predictions.json` for RNA molecules: a prediction_run, the
predicted local minima and open chain as conformations, base-pair F1 evaluations against curated secondary
structures, and the equilibrium pulling curve.

## 3. Forward model: from sequence to pulling curves

### Equilibrium (`thermo.py`)

Every secondary structure s has a folding free energy ΔG_s (ViennaRNA nearest-neighbour parameters, RNA Turner 2004
or DNA Mathews 2004, at the stated temperature and salt) and an extension set by its exterior loop: unpaired
exterior nucleotides stretch as a worm-like chain, exterior helices as rigid 2 nm rods. At force F,

    G_s(F) = ΔG_s − ∫_0^F x_s(f) df,    p_s(F) ∝ exp(−G_s(F)/kT)

Grouping structures into macrostates (nearest reference in base-pair distance) gives occupancy against force and
the mean extension, the curve an infinitely slow experiment would record (Gerland, Bundschuh & Hwa 2001; Manosas &
Ritort 2005). For long sequences the ensemble is a window above the MFE plus the structures on each reference's
unzipping path; the record says so.

### Kinetics (`kinetics.py`)

Macrostates exchange over barriers read from the lowest-saddle path between their references (ViennaRNA
findpath), with each path structure's force term added at every force. Rates obey detailed balance with the basin
free energies, so a slow enough ramp reproduces the equilibrium model exactly (tested). The master equation is
integrated over force ramps (unfolding and refolding). One prefactor k0 sets the time scale; it must be calibrated
on one measured rate. With k0 = 10³ s⁻¹ a 10-bp test hairpin hops at about 17 s⁻¹ at its midpoint force, the range
measured for DNA hairpins.

## 4. Testing thermodynamics, and measuring where it fails

Equilibrium thermodynamics predicts occupancies. A measurement that departs from that prediction is information
about the path the molecule took. The models make this a quantity, not an impression:

| Observable | Equilibrium prediction | Departure points to |
| --- | --- | --- |
| Fraction of curves showing each unfolding pattern (ΔLc, force), from segment assignments | p_m(F) from `thermo` | kinetic trapping if the fraction depends on preparation; folding history if it depends on how the molecule was made |
| Unfolding vs refolding midpoint | equal | hysteresis: the barrier, and its distance along the force coordinate |
| Midpoint force vs loading rate | constant | barrier height (Bell–Evans-like dependence, but with the transition state taken from the path, not fitted) |
| Occupancies after co-transcriptional or 5'→3' folding | p_m(0) | contingency: a fold reached first and kept |

Divergence from equilibrium is reported as the Jensen–Shannon divergence (bits) between measured (or simulated)
and equilibrium macrostate occupancies, at each force.

**Worked example (synthetic, `tests` and the demo).** A 40-nt RNA found by random search has two folds 0.13
kcal/mol apart (one long hairpin; two short hairpins) separated by a 13.8 kcal/mol barrier. At equilibrium it is
36% one hairpin and 62% two hairpins. Folding 5'→3' gives 100% two hairpins, and the model predicts this persists
for decades at zero force (slowest relaxation ≈ 2 × 10⁹ s). A pulling experiment on co-transcriptionally folded
molecules would see one unfolding pattern; on slowly annealed molecules, two. Equilibrium thermodynamics
predicts the second and not the first: the 36-point difference is the pathway effect.

### What a real test needs

Sequences with matched measurements: the construct's sequence, the handles' attachment points, the temperature
and salt, and per-curve or summary values (midpoint force, ΔLc, rates, fraction of each pattern). SMASH-BIO
records do not yet carry sequences (no entity has one) and only 17 of 967 nucleic-acid records have extracted
forces or contour lengths, so the benchmark has to be curated from papers:

1. DNA hairpins under constant force with published sequences and midpoint forces (e.g. Woodside et al. 2006,
   PNAS): tests the equilibrium model directly.
2. Riboswitch aptamers with and without ligand (adenine add and pbuE; Greenleaf et al. 2008; Neupane et al. 2011):
   tests macrostate occupancies and the effect of ligand.
3. Co-transcriptional folding under force (Frieda & Block 2012): the contingency test, with the equilibrium and
   the 5'→3' predictions side by side.
4. Frameshift-stimulating pseudoknots with several conformers (e.g. Halma et al. 2019; Neupane et al. 2021): where
   secondary-structure thermodynamics is expected to fail, and by how much.

Each benchmark entry is a `segment` set (from the paper) plus the construct sequence; the model's predictions are a
`prediction_run` with `evaluation` records. A `sequence` field on SMASH-BIO entities would let this scale.

## 5. Next steps

1. Curate the benchmark above (sequence, conditions, measured values, DOI) and add `evaluation` metrics for midpoint
   force, ΔLc and pattern fractions.
2. Calibrate k0 per molecule class on one measured rate; report all other kinetic predictions as tests.
3. Add tertiary structure where it matters: pseudoknots (ViennaRNA cannot fold them; use curated dot-brackets as
   references and their measured energies), ligand binding (a free-energy bonus on the bound reference).
4. Proteins: build folded/unfolded segment conformations from domain boundaries and coordinates, and compare ΔLc of
   each domain with SMASH-BIO contour-length increments (titin I27, talin, spectrin are in the build).
5. Learned predictors (AF-Cluster, subsampled AF2, BioEmu): import their conformations as prediction_runs and
   evaluate against observed states with `held_out` set from the training cutoff.
