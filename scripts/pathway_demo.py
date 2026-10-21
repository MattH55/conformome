#!/usr/bin/env python3
"""Equilibrium vs pathway-dependent occupancies for a synthetic bistable RNA (docs/CONFORMATIONS.md §4).

    python -I scripts/pathway_demo.py
"""
import time, numpy as np
from scipy.linalg import expm
from conformome.conformations.thermo import ForceModel, midpoint_force
from conformome.conformations.kinetics import KineticModel, cotranscriptional_start
seq="UAGCGGUCUCUCAGGCUGCUUGCCGUCCGGCCCGGCCGCG"   # synthetic, found by random search
refs={"one_hairpin":"..((((((.((..(((.....)))....))...)))))).","two_hairpins":".((((((((...)))))))).((((.......))))....","open":"."*len(seq)}
t=time.time(); m=ForceModel(seq,"rna",25.0,0.15); km=KineticModel(m,refs,k0_per_s=1e3,max_structures=400_000); print("setup %.0fs, %d structures"%(time.time()-t,len(km.ensemble)))
names=km.names; eq0=km.equilibrium(0.0); print("equilibrium at 0 pN:", dict(zip(names,np.round(eq0,3))))
start=cotranscriptional_start(m,refs); print("5'->3' sequential folding ends in:", start)
p0=np.array([1.0 if n==start else 0 for n in names]); K=km.rate_matrix(0.0)
for tt,label in [(1,"1 s"),(60,"1 min"),(3600,"1 h"),(86400,"1 day")]:
    p=expm(K*tt)@p0; print(f"  after {label:>6} at 0 pN:", dict(zip(names,np.round(p,3))))
w=np.sort(np.abs(np.linalg.eigvals(K)))[1]; print("  slowest relaxation time at 0 pN: %.3g s"%(1/w))
def mid(r): return midpoint_force(r.forces_pn,[1-x for x in r.occupancy["open"]])
for rate in (1,10,100):
    eq=km.ramp(0,30,rate); co=km.ramp(0,30,rate,start={start:1.0})
    print(f"ramp {rate:>4} pN/s: unfolding midpoint from equilibrium start {mid(eq):.2f} pN, from 5'->3' start {mid(co):.2f} pN; max JSD vs equilibrium: {max(eq.divergence()):.3f} vs {max(co.divergence()):.3f} bits")
    i=next(k for k,f in enumerate(co.forces_pn) if f>=10); print(f"     at 10 pN, 5'-start occupancies:", {n:round(co.occupancy[n][i],3) for n in names}, " equilibrium:", {n:round(co.equilibrium[n][i],3) for n in names})
