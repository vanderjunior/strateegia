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
- `/api/editais/[editalId]/summary`

## Current Capabilities

- Landing, onboarding, and dashboard aligned to the real frontend journey.
- Read-only materials, editais, and pipeline workspaces with backend/mock/offline fallback states.
- Real user-scoped materials/editais lists and material/edital summary detail reads use bounded protected endpoints through same-origin proxies.
- Controlled upload entry using the existing same-origin upload proxy path.
- PSCPP guidance workspace with profile overview, cycle, map, and question guidance.
- Study workspace with suggested sessions and dashboard study bridge.
- Product-language layer and focused Vitest/RTL safety coverage.

## Current Limitations

- Guidance-first UI: no progress mutation, scheduling, question generation, or simulado execution.
- Upload remains the only existing write path and still depends on backend/session availability.
- OCR is still presented as validation/review-oriented, not production-ready for every scanned PDF.
- Pipeline detail still has not been migrated to a dedicated bounded recent/detail endpoint.
- Auth/session UX is not finished for end users.

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
- Keep product copy on `guia flexível`, `revisão necessária`, `OCR em validação`, and `simulado em preparação`.

## Recommended Next Phases

1. Auth/session UX and backend contract audit.
2. Real user-scoped materials/editais list integration.
3. Local/staging deploy with controlled JSON/storage boundaries.
4. PostgreSQL migration planning after repository boundaries and product flows stabilize.
