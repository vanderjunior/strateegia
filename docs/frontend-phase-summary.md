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
- `/api/materials/[materialId]/study/prepare`
- `/api/materials/[materialId]/study/summary`
- `/api/study/session/next`
- `/api/study/blocks`
- `/api/editais/[editalId]/summary`
- `/api/materials/[materialId]/edital/analyze`

## Current Capabilities

- Landing, onboarding, and dashboard aligned to the real frontend journey, with normal-user surfaces simplified around the next real step.
- Read-only materials, editais, and pipeline workspaces with backend/mock/offline fallback states.
- Real user-scoped materials/editais lists plus material, edital, and pipeline detail reads use bounded protected endpoints through same-origin proxies.
- Controlled upload entry using the existing same-origin upload proxy path.
- Upload UI asks for a user-facing file classification (`Edital`, `Material de estudo`, `Prova anterior`, `Bibliografia / referência`, `Anotação / resumo`, `Outro`) before sending; the normalized `material_type` is persisted as bounded metadata and does not trigger processing.
- Materials can be grouped and filtered by persisted `material_type` in a read-only way; grouping does not trigger ingestion, OCR, generation, or study planning.
- Study material detail exposes a minimal manual `Preparar para estudo` action only for authenticated real materials classified as `study_material`; it uses deterministic no-OCR preparation and returns bounded readiness counts only.
- Study material preparation QA is closed for the minimal `.txt` path through Compose/API: authenticated upload as `Material de estudo` prepared successfully, non-study materials returned `422`, and the response stayed bounded.
- Backend `GET /api/materials/{document_id}/study/summary` and frontend same-origin `/api/materials/[materialId]/study/summary` proxy/API helper now exist as a bounded prepared-material summary contract.
- Material detail now shows a minimal read-only `Resumo do material` card for real prepared `study_material` items; summaries are conservative placeholders and do not generate questions, simulados, or progress.
- After `Preparar para estudo` succeeds on material detail, the bounded summary card refreshes in-place; if refresh fails, the UI keeps the prepare success visible and shows a safe retry-later message.
- Prepare-then-summary QA is closed through Compose/browser/API: a real `study_material` showed the not-ready summary state, refreshed in-place after `Preparar para estudo`, and displayed bounded section titles, placeholder summaries, key points, estimated minutes, and ready labels without raw content exposure.
- Backend `GET /api/study/session/next` and frontend same-origin `/api/study/session/next` now provide a minimal read-only next study session from one prepared `study_material`; it is idempotent, user-scoped, and does not mutate progress.
- Backend `GET /api/study/blocks` and frontend same-origin `/api/study/blocks` proxy/API helper now exist as a bounded read-only study-block sequence from prepared `study_material` files, with conservative edital topic/subtopic matching when safe.
- `/study` can now show `Estudo de agora` from a prepared material, including bounded section titles, placeholder summaries, key points, estimated minutes, and safe links back to the material.
- Dashboard, study, PSCPP, and editais now distinguish uploaded edital metadata from an analyzed edital; concrete study guidance is gated until real edital analysis exists.
- The frontend has an explicit read-only edital analysis state model: `no_edital_uploaded`, `edital_uploaded_not_analyzed`, `edital_analyzed`, `analysis_needs_review`, and `analysis_unavailable`.
- The state model prefers explicit bounded `analysis_status` if present and otherwise safely maps existing edital `review_state`, `coverage_status`, and `alignment_status`; it does not execute analysis.
- A same-origin proxy and API wrapper exist for controlled edital analysis; the only user-facing action is a minimal manual material-detail button for real uploaded editais.
- A same-origin proxy, API wrapper, and minimal edital detail card exist for bounded edital coverage reads; the card is read-only and does not unlock study planning.
- Material detail now exposes a minimal manual `Analisar edital` action only for authenticated real materials classified as `edital`.
- Controlled edital analysis QA is closed for the current `not_ready` path: the bounded response is preserved through `/api/editais`, the UI shows `Edital recebido` / `Análise ainda não concluída`, and the copy avoids implying analyzed topics, bibliography, coverage, or crosswalk output.
- Controlled edital analysis can now prepare fresh textual PDF editais through the backend no-OCR path; browser/API QA confirmed textual PDFs no longer remain `not_ready` solely because extraction artifacts were missing.
- OCR-required PDFs remain `not_ready`, do not trigger OCR from controlled analysis, and continue to keep study and PSCPP guidance gated.
- Editais list metrics distinguish editais enviados, análises concluídas, and items aguardando análise/conferência; visible detail links preserve encoded `edital_id` values such as `edital:...`.
- PSCPP guidance is framed as reference/demo when it is not driven by the user's analyzed edital.
- Study workspace shows a next-step empty state until a prepared study material exists, then shows a read-only material-based session. Edital-driven planning remains gated until a real analyzed edital exists.
- Editais workspace shows a clear empty state when no real edital analysis exists, including the case where an edital file was uploaded but not analyzed.
- Editais normal-user copy avoids protected-read/developer phrasing and presents edital state as a product empty state.
- Onboarding is session-aware: the first step becomes `Conta ativa` when the user is already authenticated.
- Legacy or pre-classification materials receive explanatory `Tipo não informado` guidance instead of looking like a broken zero-count dashboard.
- Left navigation now separates available areas from gated/future areas: Ciclo waits for analyzed edital, while Questões, Simulados, and Execução are marked as preparation/unavailable instead of looking active.
- Minimal internal-staging login/logout UX and simplified unauthenticated dashboard state.
- Normal user surfaces avoid staging/backend diagnostic copy; those limitations remain documented instead of foregrounded in the UI.
- Upload is visually gated by session: users must enter before the file picker and send controls are shown.
- Product-language layer and focused Vitest/RTL safety coverage.

## Current Limitations

- Guidance-first UI: no progress mutation, scheduling, question generation, or simulado execution.
- Study material preparation and the minimal next study session do not generate summaries, questions, simulados, study cycles, or progress updates.
- Study blocks have backend and frontend API contracts only; no visible UI, review-after-3 behavior, progress mutation, questions, generation, simulado, OCR, or LLM behavior has been added.
- Upload remains the only existing write path and still depends on backend/session availability.
- OCR is still presented as validation/review-oriented, not production-ready for every scanned PDF.
- Recent pipeline overview is not implemented yet; pipeline detail uses a bounded per-material summary.
- Auth/session remains intentionally minimal; there is no external provider, signup UI, or durable session store.
- Dashboard study guidance still waits for real analyzed edital context before presenting edital-driven planning; `/study` can show one material-based read-only session from prepared study material.
- Upload classification is persisted metadata only; an uploaded `edital` does not mean the edital has been analyzed.
- Controlled edital analysis remains explicit and manual; uploads still do not trigger analysis automatically, and `analysis_status=not_ready` does not unlock study or PSCPP planning.
- Edital coverage is visible only as a bounded read-only card on edital detail; it does not unlock study, PSCPP, Ciclo, Questões, Simulados, or progress.
- Scope modeling is documented in `docs/scope-model-contract-plan.md`: edital remains the official scope source, bibliography is a reference source that may be separate, study materials are learning content, and previous exams are later practice/style inputs.
- Core study flow is documented in `docs/study-core-contract-plan.md`: prepare study materials, build study blocks, show summaries, add fixation questions, reinforce errors, and review after every 3 materials before later simulados.
- Prepared material summary planning is documented in `docs/study-summary-contract-plan.md`: backend read-only placeholders and minimal material-detail UI now exist, and future generated summary work must remain bounded, user-scoped, and reviewable with no raw chunks, storage paths, progress mutation, questions, or simulado behavior.
- Textual PDF preparation inside controlled analysis is deterministic embedded-text extraction only; scanned/OCR-required PDFs still require a later explicit OCR-capable contract.
- Ciclo, Questões, Simulados, Execução, progress mutation, and multi-material study cycles are not real user capabilities yet; they remain gated or future placeholders until later contracts exist.

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

1. EditalTaxonomy-A: refine bounded edital taxonomy around area/topic/subtopic before more coverage work.
2. StudySession-QA-A: browser/API QA for the minimal read-only next study session.
3. Coverage-QA: validate browser, API, no-leakage, and conservative gating for the edital coverage card.
4. StudyBlocks-C: add minimal `/study` rendering for the bounded study-block read while keeping the existing one-material session fallback.
5. PostgreSQL migration planning only after repository boundaries and real-user flows stabilize.
