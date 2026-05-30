# Frontend Phase Summary

## Implemented Routes

- `/`
- `/dashboard`
- `/onboarding`
- `/materials`
- `/materials/upload`
- `/materials/[materialId]`
- `/editais`
- `/editais/[editalId]`
- `/pipeline/[documentId]`
- `/pscpp`
- `/pscpp/mapa`
- `/pscpp/ciclo`
- `/pscpp/questoes`
- `/study`
- `/study/session/[sessionId]`
- `/api/materials/upload`
- `/api/materials/[materialId]/summary`
- `/api/materials/[materialId]/pipeline/summary`
- `/api/editais/[editalId]/summary`

## Current Capabilities

- Landing, onboarding, and dashboard aligned to the real frontend journey, with normal-user surfaces simplified around the next real step.
- Read-only materials, editais, and pipeline workspaces with backend/mock/offline fallback states.
- Real user-scoped materials/editais lists plus material, edital, and pipeline detail reads use bounded protected endpoints through same-origin proxies.
- Controlled upload entry using the existing same-origin upload proxy path.
- Upload UI asks for a user-facing file classification (`Edital`, `Material de estudo`, `Prova anterior`, `Bibliografia / referência`, `Anotação / resumo`, `Outro`) before sending; the normalized `material_type` is persisted as bounded metadata and does not trigger processing.
- Materials can be grouped and filtered by persisted `material_type` in a read-only way; grouping does not trigger ingestion, OCR, generation, or study planning.
- Dashboard, study, PSCPP, and editais now distinguish uploaded edital metadata from an analyzed edital; concrete study guidance is gated until real edital analysis exists.
- The frontend has an explicit read-only edital analysis state model: `no_edital_uploaded`, `edital_uploaded_not_analyzed`, `edital_analyzed`, `analysis_needs_review`, and `analysis_unavailable`.
- The state model prefers explicit bounded `analysis_status` if present and otherwise safely maps existing edital `review_state`, `coverage_status`, and `alignment_status`; it does not execute analysis.
- PSCPP guidance is framed as reference/demo when it is not driven by the user's analyzed edital.
- Study workspace shows a next-step empty state until a real analyzed edital exists; demo orientations are clearly labeled as examples.
- Editais workspace shows a clear empty state when no real edital analysis exists, including the case where an edital file was uploaded but not analyzed.
- Editais normal-user copy avoids protected-read/developer phrasing and presents edital state as a product empty state.
- Onboarding is session-aware: the first step becomes `Conta ativa` when the user is already authenticated.
- Legacy or pre-classification materials receive explanatory `Tipo não informado` guidance instead of looking like a broken zero-count dashboard.
- Minimal internal-staging login/logout UX and simplified unauthenticated dashboard state.
- Normal user surfaces avoid staging/backend diagnostic copy; those limitations remain documented instead of foregrounded in the UI.
- Upload is visually gated by session: users must enter before the file picker and send controls are shown.
- Product-language layer and focused Vitest/RTL safety coverage.

## Current Limitations

- Guidance-first UI: no progress mutation, scheduling, question generation, or simulado execution.
- Upload remains the only existing write path and still depends on backend/session availability.
- OCR is still presented as validation/review-oriented, not production-ready for every scanned PDF.
- Recent pipeline overview is not implemented yet; pipeline detail uses a bounded per-material summary.
- Auth/session remains intentionally minimal; there is no external provider, signup UI, or durable session store.
- Dashboard study guidance waits for real analyzed edital context before presenting a concrete study orientation.
- Upload classification is persisted metadata only; an uploaded `edital` does not mean the edital has been analyzed.

## Validation Commands

Run from `frontend/`:

```bash
npm run test
npm run typecheck
npm run build
```

Additional audit checks:

```bash
rg -n -i 'correct_answer|correct_option|answer_key|answer_key_value|final_answer_key|final_answer_key_content|gabarito|gabarito_final|correctness|is_correct|raw document body|raw OCR text dump|OCR/base64 payload|password_hash|session token|private path/storage root|/Users/|C:\\' app components lib/mock lib/adapters lib/api lib/product
rg -n -i 'pricing|plano gratuito|plano profissional|plano intensivo|assinatura|comprar|checkout' app components lib/mock lib/adapters lib/api lib/product
```

## Safety Boundaries

- Do not expose answer keys, gabarito, raw OCR dumps, raw document bodies, or local/private paths.
- Do not add progress apply, scheduler/calendar mutation, question generation actions, or simulado generation/execution without a separate approved phase.
- Keep product copy truthful: demo/reference guidance must not appear as a personalized plan before a real analyzed edital exists.
- Keep upload classification copy truthful: `material_type` is metadata only and must not imply automatic ingestion, OCR, generation, or study planning.

## Recommended Next Phases

1. Authenticated browser QA closeout for the current Compose staging build.
2. Decide whether to keep improving internal staging UX or begin a narrow edital-analysis planning phase.
3. PostgreSQL migration planning only after repository boundaries and real-user flows stabilize.
