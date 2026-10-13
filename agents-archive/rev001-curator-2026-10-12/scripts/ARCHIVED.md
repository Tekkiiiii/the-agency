# mem-graph-build.py - ARCHIVED 2026-10-12

Retired with the rest of the REV001 memory consolidation (live commit f19818f). The script built a derived
memory graph (nodes and links over the memory files) that the Graphify lookup layer and 8 scorecard checks
(R3, S1, S2, S3, S4, S6, S8, S10) read. Both are retired: project knowledge is looked up directly
(runbooks/service-lookups.md, section "Project knowledge"), and link health is covered by scorecard check R2 plus
the lint-memory skill. Byte-identical to the file before archiving.

Callers repointed or removed: `scripts/mem` (the `graph` subcommand is gone), `scripts/mem-gardener.sh` (step 4
"Rebuild" no longer runs), `scripts/mem-scorecard.py` (graph checks marked RETIRED, excluded from scoring).

Restore: `git mv agents-archive/rev001-curator-2026-10-12/scripts/mem-graph-build.py scripts/mem-graph-build.py`,
then re-add the `graph` case in `scripts/mem`, the rebuild call in `scripts/mem-gardener.sh`, and un-retire the graph
checks in `scripts/mem-scorecard.py`.
