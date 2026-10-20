# Coding agent

Start here: [agent-handoff/AGENT_INSTRUCTIONS.md](agent-handoff/AGENT_INSTRUCTIONS.md).

Branch: `paper/ore`.

The task is in the handoff file. Finish the nucleic-acid scope, or cut the manuscript claims that the build does not support, before tagging a release. The conflict rule is now 3σ with pairwise conditions (`conformome/mapping/conflicts.py`); do not put back the 1σ binning. Downloads keep a record only when `docs/SOURCES.md` says `redistribute: yes` and `provenance.licence` is listed in `zenodo/redistribution.yaml`. Open the pull request into `ccr-ebb336f7-3qzi9h`. Do not publish a GitHub release or a Zenodo record. Do not rename the default branch from this file.
