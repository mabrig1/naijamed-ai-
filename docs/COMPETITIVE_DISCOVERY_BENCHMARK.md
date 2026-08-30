# NigerFlora Competitive Discovery Benchmark

## GitHub projects reviewed

### Cytoscape Web
Repository: https://github.com/cytoscape/cytoscape-web

Competitive strengths:
- browser-native biological network visualization;
- network/table workspaces;
- layout, filtering and export workflows;
- project-oriented interaction rather than static reports.

NigerFlora response:
- add a lightweight interaction-network evidence workspace now;
- preserve node/edge provenance and exportable JSON;
- leave advanced Cytoscape-compatible import/export as a later extension.

### AutoDock Vina
Repository: https://github.com/ccsb-scripps/AutoDock-Vina

Competitive strengths:
- established open-source docking engine;
- batch docking / virtual screening;
- configurable search space, exhaustiveness and pose count;
- reproducible command/parameter workflows.

NigerFlora response:
- generate AutoDock Vina-compatible screening manifests;
- preserve receptor/ligand source identifiers and search-box parameters;
- mark jobs `ready_for_worker` rather than fabricate scores on Vercel;
- use a separate compute worker for native Vina execution when added.

### MolDock / LCBC-Dock
Repository: https://github.com/wonmor/LCBC-Dock

Competitive strengths:
- browser/mobile docking workflow;
- public protein and compound database search;
- job submission and result visualization.

NigerFlora response:
- add PubChem compound lookup;
- add RCSB PDB structure lookup;
- save compounds and proteins in a persistent user library;
- connect the library directly to screening-manifest creation.

### Computational Drug Discovery Dashboard
Repository: https://github.com/Chicone/drug-discovery-dashboard

Competitive strengths:
- unified molecular-design, docking, ADMET, simulation and report workflow;
- compound/project library;
- docking run history;
- scientific export and reproducibility focus.

NigerFlora response:
- create one Discovery Workbench rather than fragmented tools;
- persist compound/protein assets, screening jobs and interaction networks;
- provide reproducibility history and JSON manifest export;
- retain Research Studio monetization as a separate service layer.

## Features integrated in this upgrade

1. PubChem compound finder by name or CID.
2. RCSB PDB protein-structure finder.
3. User-specific compound and protein library in MongoDB Atlas.
4. AutoDock Vina-compatible virtual-screening manifests.
5. Search-space, exhaustiveness, pose-count and seed controls.
6. Screening job history with downloadable JSON manifests.
7. Interaction-network evidence builder and visual preview.
8. Saved network history and export.
9. Scientific boundary that prevents computational associations from being presented as validated efficacy or synergy.

## Deliberately not implemented on Vercel

Native AutoDock Vina, GROMACS or molecular-dynamics workloads are not executed inside the Vercel serverless runtime. NigerFlora prepares reproducible manifests and stores job state; a future dedicated compute worker can consume these manifests. This avoids false results, brittle native-binary deployment and oversized serverless functions.

## Next competitive extensions

- dedicated GPU/CPU worker adapter for Vina jobs;
- signed worker callbacks and result-artifact storage;
- 3D protein/ligand viewer using a browser molecular renderer;
- interaction fingerprints and contact summaries;
- Cytoscape CX2 import/export;
- production-validated ADMET/QSAR models with model cards;
- report builder combining provenance, methods, parameters, figures and results;
- project collaboration and reviewer comments.
