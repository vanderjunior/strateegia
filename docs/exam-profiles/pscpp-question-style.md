# PSCPP Question Style Profile

`marinha_dpc_pscpp_praticagem` is the canonical StudyFlow AI question-style profile for Marinha/DPC PSCPP Praticagem question-generation metadata.

## Scope

- Source-grounded, technical-operational, bibliography-heavy multiple-choice style
- Intended for `simulado`, `fixation`, `review`, and `summary_reading` question-generation metadata
- Profile-only foundation: no runtime apply, no ledger mutation, no ranking, no scheduler behavior

## Historical Evidence

- `PSCPP/2012 Prova Rosa` is treated only as historical style and archetype evidence
- It must not be treated as current edital content scope, current bibliography truth, or current syllabus truth
- Current edital alignment remains required

## Core Rules

- A-E multiple-choice format with five alternatives
- Explicit source and bibliography anchor required
- Source title should remain visible in blueprint metadata and is preferred in the stem template
- Numeric/calculation items require explicit source or formula support
- Multi-statement items require source support per statement
- Negative-command items should be marked for review
- Final answer key remains human-review-only and source-validation-dependent

## Common Archetypes

- Statement combination
- True/false sequence multiple choice
- Incorrect alternative
- Applied calculation
- Technical operational scenario
- Technical gap fill
- Normative case application

## Scoring Hints

- Historical observed weights include `0.8`, `1.0`, `1.2`, `1.3`, `1.6`, and `2.0`
- Weight must come from edital or blueprint evidence
- No uniform default weight should be assumed

## Distractor Policy

- Distractors must stay technically plausible
- Common maritime confusions include:
  - `BE_vs_BB`
  - `proa_vs_popa`
  - `vento_vs_corrente`
  - `aguas_rasas_vs_aguas_profundas`
  - `squat_vs_bank_effect`
  - `direct_towing_vs_indirect_towing`
  - `regra_COLREG_vs_excecao`
  - `rumo_verdadeiro_vs_rumo_magnetico_vs_rumo_da_agulha`

## Safety

- No answer key or gabarito output
- No OCR/base64 or raw document body in profile metadata
- No LLM, RAG, or vector behavior
- No runtime apply or progress mutation

## Generation Integration

- The PSCPP profile enriches metadata for `simulado`, `fixation`, `review`, and `summary_reading`
- Source-grounding validation checks source presence, bibliography anchor visibility, source-title visibility, and current edital alignment
- Archetype validation keeps PSCPP generation within the allowed maritime archetype set and adds review markers when constraints are missing
- Scoring and distractor hints stay metadata-only and deterministic
- Answer-key handling remains human-review-only
- `PSCPP/2012 Prova Rosa` remains historical style evidence only, never current edital scope
- Related study guidance lives in `pscpp-study-cycle-profile.md`
