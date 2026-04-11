# Test Data

A synthetic test dataset is provided for pipeline validation. It is built around a well-characterised protein with known mutations and expected outputs.

---

## Reference protein

The test dataset uses **Green Fluorescent Protein (GFP)** from *Aequorea victoria* (UniProt accession [`P42212`](https://www.uniprot.org/uniprotkb/P42212)). GFP was chosen because its mutation landscape is extensively characterised in the literature, making it possible to verify that the pipeline correctly identifies, classifies, and scores known variants.

## Plasmid

The wild-type plasmid is a **pET-28a(+)** expression vector containing a codon-optimised GFP coding sequence:

- **CDS length:** 717 bp
- **Protein length:** 238 amino acids (including the initiator methionine)
- **Stop codon:** TAA

The plasmid FASTA file is provided in standard single-sequence format.

## Variant dataset

The dataset contains **11 records**: one wild-type control (Variant 0) and ten Generation 1 mutants (Variants 1–10). Each record includes the full linearised plasmid sequence, DNA quantification in femtograms, and protein quantification in picograms. The data is available in both **TSV** and **JSON** formats.

The ten variants were designed to exercise different branches of the analysis pipeline:

### Single missense mutations

Variants **1 (S65T)**, **2 (F64L)**, **4 (Y66H)**, **5 (T203Y)**, and **7 (Y66W)** each carry one amino acid substitution at known positions in the GFP chromophore or beta-barrel.

### Double missense mutations

Variants **3 (S65T + F64L)**, **6 (S65T + T203Y)**, and **10 (V150A + S65T)** carry two substitutions, testing the pipeline's ability to detect multiple mutations per variant.

### Silent mutation

Variant **8 (L15L)** introduces a synonymous codon change (`CTG → CTT`) that alters the DNA but not the protein, verifying that the mutation caller correctly distinguishes synonymous from non-synonymous changes. (The protein-level aligner should report zero mutations for this variant — see [Mutation Calling](../pipeline/mutation-calling.md).)

### Nonsense mutation

Variant **9 (Q80\*)** introduces a premature stop codon (`CAG → TAG`), producing a truncated protein. This tests the pipeline's handling of nonsense mutations and their effect on activity scoring.

## Expected results

The quantification values were chosen to produce biologically plausible activity scores:

- **Well-known beneficial mutations** (S65T, the classic EGFP mutation; S65T + F64L, the standard EGFP double mutant) produce **positive** activity scores.
- **Deleterious mutations** (Q80* nonsense, Y66W chromophore destabilisation) produce **negative** scores.
- **Silent mutation** L15L produces a **near-zero** score.

The full set of expected mutation counts, mutation types, and activity scores is documented alongside the data files for verification.

## Circular plasmid handling

Each variant's assembled DNA sequence is linearised at a **different random offset** to simulate real sequencing assembly data. This means the ORF start and end positions vary across variants despite all carrying the same 717 bp coding sequence — exercising the circular plasmid handling logic in the ORF detection module.
