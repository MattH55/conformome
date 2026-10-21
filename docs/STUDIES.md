# Studies: constructs, protocols, state networks and occupancies

A single-molecule study is more than a list of rips. It has a **construct** (the molecule actually pulled), one or
more **protocols** (how it was pulled, and what was done to it before each pull), a **state network** (the states
seen, the transitions between them, the pathways trajectories follow, and what perturbations do), and
**occupancies** (how often each state or pathway is seen, as counts). Each study lives in `studies/<name>/`:

| File | Schema | Holds |
| --- | --- | --- |
| `construct.json` | `construct` | Reference sequence and region, studied sequence, variant, handles, attachment chemistry |
| `protocols.json` | `protocol` (list) | Instrument, mode (ramp, constant force, jump), loading, **preparation history**, perturbations (antisense oligos, ligands, ions), solution, elastic model, assignment method, numbers of molecules and curves |
| `network.json` | `state_network` | States (with structure, measured and predicted ΔLc, and the evidence used to assign them), transitions (ΔLc, force distribution, rates, distance to the transition state, barrier), pathways, perturbation effects (abolishes / creates / stabilizes / retains), functional readouts (e.g. frameshift efficiency), derived metrics (e.g. conformational plasticity) |
| `occupancies.json` | `occupancy` (list) | Counts per state or pathway, the total, 95% intervals, and comparisons with equilibrium or kinetic predictions (divergence in bits) |

Protocol fields follow the groups of the FAIR reporting standard for optical tweezers experiments (Halma et al.,
Biophys. J. 2025): hardware → `instrument`, assay → `mode`/`loading`/`preparation`/`perturbations`, solution →
`conditions`, analysis → `elasticity_model`/`analysis`.

The four criteria used to assign force-spectroscopy states map onto fields:

1. contour-length change matches the structure → `delta_lc_from_unfolded` vs `predicted_delta_lc`;
2. forces consistent with stability → transition `force` and `barrier_kt`;
3. a coherent transition map → `transitions` and `pathways`;
4. perturbations remove the states they should → `perturbation_effects`.

Each state lists which of these support it (`assignment_evidence`).

## Rules

* Nothing is estimated to fill a gap. A value the curator cannot read is `null` and named in `curation.missing`, and
  a record with missing values cannot be `complete` (the validator enforces this).
* Values computed by Conformome (for example a predicted ΔLc) carry their method and assumptions, and are never put
  in a measured field.
* Occupancies are counts out of a total wherever the source gives them; fractions and Wilson 95% intervals follow.
* `preparation` is required: an occupancy measured after holding at low force for 1 s is not the same quantity as
  one measured after co-transcriptional folding, and only the comparison between them separates history from
  equilibrium.

## First study: West Nile virus NS1' frameshift signal (Halma et al., PNAS 2019)

`studies/wnv-ns1prime-frameshift/` encodes what could be read from the MSc thesis on which the paper builds: the
construct's origin (RefSeq NC_009942), buffer, beads, the force-ramp protocol and the two antisense oligos, the
states (PKS, S1, the 3' hairpin of PKS, the 38- and 71-nt hairpins of the stem-loop fold, PKL), the three pathways,
the oligo 1 effect (abolishes PKS, retains S1), the frameshift efficiency (~70%) and the plasticity metric. Predicted
ΔLc for the states with stated lengths are computed upper bounds.

Still to fill from the paper (all `null` now):

- [ ] construct sequence and its coordinates in NC_009942; handle type and length; which end has which attachment
- [ ] temperature; pulling speed or loading rate; trap stiffness; refolding force and wait between cycles
- [ ] elastic-model parameters (handles and unfolded RNA)
- [ ] number of molecules and curves per protocol
- [ ] measured ΔLc and unfolding forces per state and per transition; the transition map and intermediates
- [ ] occupancies: trajectories per pathway, and the total, per protocol (with and without each oligo)
- [ ] the definition of S1; the effect of oligo 2; the new structures formed with oligo 1
- [ ] dot-bracket structures for each state (needed for the equilibrium comparison)
- [ ] the plasticity value for WNV

Once the sequence and dot-brackets are in, `studies.equilibrium_comparison` gives the predicted equilibrium
occupancy at each force window and the divergence from the measured one. The pseudoknots (PKS, PKL) are outside the
nested secondary-structure model, so for this molecule the comparison is expected to fail; how badly is the result.
