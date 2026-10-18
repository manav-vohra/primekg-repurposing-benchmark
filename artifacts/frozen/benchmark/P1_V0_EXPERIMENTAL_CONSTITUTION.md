# P1 Track A v0 — Experimental Constitution

Status: FROZEN

Benchmark ID: P1_TRACK_A_PRIMEKG_V0

## 1. Scientific question

Test whether relative expert utility across disease-level
zero-shot therapeutic indication-ranking queries is
heterogeneous, stable, and predictable from legal pre-label
disease descriptors.

This benchmark evaluates expert applicability before any
learned router is introduced.

## 2. Canonical graph

Dataset: PrimeKG

Canonical graph file:
`/content/drive/MyDrive/P1/PrimeKG/kg.csv`

Directed edge records: 8,100,498

Drug nodes: 7,957

Disease nodes: 17,080

Gene/protein nodes: 27,610

PrimeKG file SHA-256:

`0a5a010fcd88dcec572a573d98c26c1c244a11567092b6161d3ded611cfb5c69`

## 3. Candidate universe

Every query uses the same candidate universe:

7,957 PrimeKG DrugBank drug nodes.

Candidate membership is NOT conditioned on:
- known indication status
- target availability
- non-therapeutic edge availability
- expert-specific representation availability

Representation failure is an expert applicability property,
not a candidate eligibility rule.

## 4. Primary disease cohort

A disease is eligible for P1-v0 if it has at least:

3 CLEAN_INDICATION pairs.

Primary disease count:

738

Each disease is evaluated exactly once out of fold.

## 5. Therapeutic label roles

Primary positive:

CLEAN_INDICATION

Ignored in primary ranking metrics:

- AMBIGUOUS_INDICATION
- OFFLABEL_ONLY
- CONFLICTING_NONINDICATION

Remain in the ranking universe:

- CONTRAINDICATION_ONLY
- UNOBSERVED

UNOBSERVED does not mean true negative.

Contraindications are explicit safety annotations and are
evaluated separately rather than collapsed into generic
negative labels.

## 6. Ontology leakage control

Primary OOF design:

K = 8

Seed = 42

For each evaluation fold, all therapeutic relations are hidden
for:

1. evaluation target diseases
2. every direct disease_disease ontology neighbor of a target
   that possesses any indication annotation

These neighboring diseases are quarantine/buffer diseases.

All allowed non-therapeutic KG evidence remains available,
including disease ontology edges.

Direct indication-positive ontology leakage under this
protocol must equal zero.

## 7. Primary evaluation metrics

Primary disease-level ranking metrics:

- Recall@K
- Hit@K
- MRR
- first-hit rank

Results are macro-averaged over diseases.

Safety diagnostics:

- Contraindication@K
- contraindication intrusion rate

Secondary diagnostic metrics:

- AUPRC
- AUROC

AUROC/AUPRC must not define the principal scientific result
because unobserved drug-disease pairs are not established
true negatives.

## 8. Information parity

Track A requires identical:

- canonical graph snapshot
- candidate universe
- fold assignment
- target masking
- ontology quarantine
- therapeutic information policy
- evaluation truth
- metric implementation

across all experts unless a deviation is explicitly recorded
as a protocol violation or separate Track B experiment.

## 9. Expert outputs

Every expert must produce, for every evaluated disease:

- score or ranking over the canonical candidate universe
- uncertainty if available
- applicability / failure status
- runtime / compute cost
- provenance
- seed
- protocol version

These outputs feed the Expert Matrix.

## 10. Benchmark immutability

After this constitution is frozen, any change to:

- candidate universe
- disease eligibility
- label policy
- fold assignment
- quarantine policy
- canonical graph
- primary metric semantics

requires a new benchmark version.

Benchmark manifest SHA-256:

`86b9f4f65fcc981eec8a188779d884e852815da01d9ce9b6a6733868d8a38f53`
