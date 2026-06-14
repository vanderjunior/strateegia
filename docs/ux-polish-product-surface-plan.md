# UX Polish Product Surface Plan

## 1. Executive summary

The product now has a complete minimum study path: users can authenticate, upload/analyze an edital, upload/prepare study materials, study blocks, answer objective fixation questions, receive conservative feedback/reinforcement, explicitly mark blocks as studied, and see progress/review summaries.

The main UX risk is no longer missing backend capability. The main risk is that the user-facing surfaces now compete for attention:

- `/study` asks the user to parse the study path, cumulative review, progress summary, and several block cards before the dominant next action fully settles.
- Block detail is functionally safe, but summary, questions, answer review, reinforcement, and study registration can feel like separate stacked products instead of one guided study moment.
- Navigation and shell copy still expose product-development language such as beta/experimental framing, route labels, future surfaces, and status badges before the user reaches the task.
- Materials/editais screens are safe, but classification/status/card density makes it harder to understand the distinction between edital scope and study content.

Recommended first phase: `UX-Polish-B`, a behavior-preserving copy and state-message cleanup. It should remove or demote internal/product-development language, consolidate repeated cautions, and make one primary action per state clearer before layout changes.

## 2. Current product journey

Observed target journey:

1. User logs in.
2. User sends or opens an edital and waits for analysis.
3. User uploads a study material and prepares it.
4. User opens `/study`.
5. User identifies what to do next.
6. User opens a study block.
7. User reads summary and key points.
8. User answers a fixation question.
9. User reviews the selected choice.
10. User sees feedback and reinforcement.
11. User marks the block as studied.
12. User returns to `/study`.
13. User understands progress and cumulative review.

The flow is understandable with product context, but it is not yet one-scan clear. A new user can complete the path, yet the interface often explains safety/state constraints before it clearly says the next study action.

## 3. Surface inventory table

| Surface | Primary objective | Primary action | Secondary actions | Observed problem | User impact | Severity | Proposed direction | Behavior unchanged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/` landing | Understand what Mentorium does and enter the app | Comece sua preparação | Ver study/material/map references | Multiple repeated CTAs, future surfaces, beta/pipeline-like product language, and progress-sounding examples appear before the core value is concise | User may expect more complete automation than the workspace actually provides | P1 | Tighten landing around current real flow and move future capability copy lower | Yes |
| `/login` | Enter account | Entrar | Voltar ao painel | In authenticated state it still sits inside the full app shell, so nav/status competes with the form | Login is usable but visually heavier than necessary | P2 | Keep form dominant; reduce surrounding shell noise on auth pages | Yes |
| Dashboard | Know the next real step | Continue current study step or upload needed item | Materials, editais, PSCPP references | Multiple cards suggest next steps at once; status summaries duplicate workspace routes | User may hesitate between dashboard, study, materials, and editais | P1 | Make dashboard a single next-step launcher with compact secondary summaries | Yes |
| `/materials` | Find or upload study inputs | Enviar material | Filter/group, Ver detalhes | Many group chips, filter chips, repeated cards, and repeated `Ver detalhes` actions create high density | User sees all data before knowing which material needs action | P1 | Surface actionable material states first; compact grouping/filter chips | Yes |
| Material detail | Understand and prepare/open one material | Preparar para estudo or Analisar edital when applicable | Open summaries, return to list | Status/readiness cards can compete with the one real action | User may parse lifecycle state before seeing what to do | P1 | Put primary action near top and make status support it | Yes |
| `/materials/upload` | Classify and upload a file | Enviar arquivo | Choose material type | Flow is mostly clear; explanatory validation copy can be compressed | Minor extra reading before upload | P2 | Keep classification but shorten helper text | Yes |
| `/editais` | Understand edital analysis state | Ver edital or send/analyze edital | Review metrics | Metrics/status can appear more important than next step | User may not know whether edital is scope, content, or review material | P1 | Frame edital as scope first; demote metrics | Yes |
| Edital detail | Understand scope and coverage | Use coverage to choose material/upload next item | View items, return | Coverage metrics and source/status badges create a technical-feeling detail page | User may over-focus on coverage counts instead of study action | P1 | Use a short scope summary plus next material gap/action | Yes |
| `/study` | Continue studying | Estudar bloco / Continuar estudando | Review, progress, materials | Review and progress cards sit near the top and compete with study blocks | The primary next action is diluted | P0 | Reorder hierarchy around next block first, then path, then compact review/progress | Yes |
| `/study/blocks/[blockId]` | Study one block | Read summary, answer, then mark studied | Open material, return to path | Dense sequence: header, actions, summary, key points, questions, duplicated alternatives, feedback, reinforcement, cautions, progress control | User may treat answer/progress as the main task before learning content | P0 | Make summary/key points primary; remove duplicate alternatives; group post-answer panels | Yes |
| AppShell/navigation | Orient across the app | Navigate to current areas | Future/gated areas | Mobile shows long sidebar/status stack before content; desktop nav includes future labels/statuses | User reaches work only after product status noise | P0 | Keep active core nav prominent; collapse future/gated items and compress mobile shell | Yes |

## 4. `/study` analysis

Observed at desktop width:

- Headings include `Estudo guiado`, `Seu caminho de estudo`, `Blocos conectados ao edital`, `Revisão acumulada sugerida`, `Acompanhamento do estudo`, and `O que estudar agora`.
- Actions include `Ver materiais`, `Continuar estudando`, and repeated `Estudar bloco`.
- The page safely rendered studied-material copy only because the API returned `studied_materials`, and it did not expose forbidden completion/score/gabarito language.

Observed at mobile width `390x844`:

- No horizontal overflow was observed.
- The top of the page is dominated by shell/nav/status text before content: product label, access/status copy, session state, dashboard/materials/editais/study/future nav items, header, beta badge, then page content.
- The mobile stack can show a not-ready/demo-like state if hydration/session data is not yet settled, so loading/ready transitions should be visually calmer.

Preferred hierarchy:

1. Continue studying / next recommended block.
2. Study path and block list.
3. Review due/suggested only when actionable.
4. Compact progress summary.
5. Supporting guidance and materials links.

Issues and directions:

| Surface | Observed problem | User impact | Severity | Proposed direction | Behavior unchanged |
| --- | --- | --- | --- | --- | --- |
| `/study` | Review/progress cards appear before the actual block cards | User may not know whether to study, review, or inspect progress | P0 | Move next block/action above review/progress; keep review/progress compact | Yes |
| `/study` | Review card repeats counts, summary items, question readiness, reinforcement, cautions, and links | Useful but too much for secondary guidance | P1 | Convert to compact `Revisão acumulada` row/card with expandable details later | Yes |
| `/study` | Progress card uses multiple counters and cautions | It competes with study action | P1 | Keep 2-3 most relevant counters visible and move caution to one short line | Yes |
| `/study` | Not-ready/partial states can occupy full-card space | Empty guidance can feel like a blocker even when blocks exist | P1 | Hide or collapse non-actionable review/progress states when study blocks exist | Yes |

## 5. Block-detail analysis

Observed at desktop width:

- The page renders `Estudar bloco`, topic title, `Resumo do bloco`, `Questões de fixação`, five radio options, `Revisar escolha`, and `Marcar bloco como estudado`.
- Selecting an option and clicking `Revisar escolha` showed safe feedback without forbidden score/gabarito/correctness language.
- Radio controls are usable, but alternatives are visually heavy and can be duplicated by nearby display-only option lists.

Observed at mobile width `390x844`:

- No horizontal overflow was observed.
- Radio options remain tappable as stacked labels.
- The user must scroll through the same long shell/nav stack before reaching the block content.

Issues and directions:

| Surface | Observed problem | User impact | Severity | Proposed direction | Behavior unchanged |
| --- | --- | --- | --- | --- | --- |
| Block detail | Summary/key points and study registration compete with questions/progress controls | User may skip reading and jump to interaction | P0 | Put summary/key points first; place `Marcar bloco como estudado` after learning content or as a secondary end action | Yes |
| Block detail | Alternatives can appear both as display-only alternatives and radio labels | Duplicated choices increase visual density | P0 | For objective questions, render alternatives once as the interactive radio group | Yes |
| Block detail | Feedback, reinforcement, and caution copy can become several panels | Post-answer state is safe but verbose | P1 | Combine into one `Orientação após revisão` group with `Feedback` and `Reforço sugerido` subsections | Yes |
| Block detail | `Abrir material`, `Voltar ao caminho`, and study registration are all near the task | The main learning action can feel unclear | P1 | Make navigation links secondary and keep one dominant action per phase | Yes |
| Block detail | Mobile shell pushes block content down | Small-screen study starts late | P2 | Compress mobile shell/navigation before block content | Yes |

## 6. Materials/editais analysis

User distinction should be:

- Edital: defines the study scope and must be analyzed.
- Material de estudo: provides learning content and must be prepared.
- Revisão acumulada: consolidates already available or studied content.

Observed issues:

| Surface | Observed problem | User impact | Severity | Proposed direction | Behavior unchanged |
| --- | --- | --- | --- | --- | --- |
| Materials list | Category tiles, filters, cards, and repeated detail links all appear together | Harder to find the next material needing action | P1 | Show actionable materials first; move category overview below or make it compact | Yes |
| Materials list | Test-like filenames and `Tipo não informado` groups can dominate local QA data | Real product meaning is harder to infer in staging | P2 | Improve display names/fallback labels; keep fixture names in QA docs | Yes |
| Material detail | Preparation/action state is one of several cards | User may not see the important action immediately | P1 | Elevate `Preparar para estudo` / analyzed-state action above metadata | Yes |
| Editais list | `Editais em análise preliminar` plus metrics can sound like a technical queue | User may not know the next action | P1 | Lead with `Seu edital define o escopo`; then show state/action | Yes |
| Edital detail | Coverage/counts/gaps are useful but technical | User may not know how coverage informs study | P1 | Translate coverage into next material/study guidance | Yes |

## 7. Navigation/layout analysis

Observed AppShell/navigation issues:

- The sidebar includes available routes, gated routes, reference routes, and future/unavailable routes in one visual stack.
- Labels such as `Depende de edital`, `Aguardando edital analisado`, `Referência`, `Em preparação`, and `Ainda não disponível` are truthful, but they create a status wall.
- Header eyebrows include route/product-development framing such as `mentorium / pipeline`, `mentorium / estudo / sessão`, and `beta fechado`.
- Mobile puts the full sidebar, session state, and future-route labels above page content.

Recommended direction:

- Primary nav should emphasize the current core: Dashboard, Materiais, Editais, Estudo.
- Gated/future routes should move into a compact secondary area or remain hidden until useful.
- Header should describe the user task, not the internal route.
- Mobile should use a collapsed menu or compact top nav so content begins quickly.

## 8. Copy vocabulary

Preferred product vocabulary:

- Edital
- Analisar edital
- Material de estudo
- Preparar para estudo
- Seu caminho de estudo
- Continuar estudando
- Estudar bloco
- Resumo
- Pontos principais
- Questões de fixação
- Revisar escolha
- Orientação de estudo
- Reforço sugerido
- Marcar bloco como estudado
- Acompanhamento do estudo
- Revisão acumulada

Use carefully:

- Materiais estudados only when the backend returns `studied_materials`.
- Bloco marcado como estudado only after explicit user action.
- Questões revisadas nesta etapa, not scored or corrected.

Avoid visible normal-user terms:

- backend
- pipeline
- chunk
- metadata
- protected read
- ledger
- guardrail
- shell
- runtime chain
- artifact
- audit
- deterministic
- owner scope
- internal lifecycle enum names
- material concluído
- progresso atualizado
- pontuação
- score
- gabarito
- resposta correta
- gerar simulado

## 9. Loading, empty, and error-state analysis

State principles:

- Loading should be brief and local to the affected card.
- Empty states should give one next action, not a long explanation.
- Auth-required states should show `Entrar` as the action.
- Backend/unavailable states should say the user can try again later without using backend/internal language.
- `needs_review` should be concise and not look like a blocking error when content is usable.
- Success states should not imply completion unless the backend semantics support it.

Observed issues:

| State | Problem | Direction |
| --- | --- | --- |
| not_ready | Often rendered as full card even when not actionable | Hide or compact when another primary path exists |
| partial | Can resemble an error or a separate task | Use one-line guidance and keep primary study action visible |
| needs_review | Accurate but repeated across cards | Use a shared short label and detailed explanation only once |
| success | `Bloco marcado como estudado` is safe, but nearby copy must avoid material completion | Keep caution short and adjacent |
| unavailable | Some API helper codes remain technical in code/tests, while UI is mostly safe | Continue mapping to product-safe copy |

## 10. Responsive and accessibility observations

Responsive observations:

- Desktop `1280x720` showed functional layouts but high vertical card density on `/study` and block detail.
- Mobile `390x844` showed no horizontal overflow on `/study` or block detail.
- Mobile content starts too low because the shell/sidebar/status stack appears before the page task.
- Multi-column metric cards collapse, but repeated cards create long scrolling.

Accessibility basics:

- Heading hierarchy is mostly present, but repeated card titles can create many same-level headings.
- Radio alternatives are label-backed and usable.
- Button wording is generally explicit.
- Disabled/future nav labels include text, not only color.
- Some uppercase microcopy and muted text may be small/low-emphasis for important guidance.
- Focus and keyboard behavior were not formally certified in this audit.

## 11. Prioritized backlog

### P0 - clarity/safety

- Make `/study` next action dominant before review/progress summaries.
- Remove duplicate objective alternatives from block detail so choices appear once.
- Reduce visible internal/product-development language in AppShell/header and normal workspace copy.
- Ensure only one dominant primary action per state.
- Keep completion/correction/scoring boundaries explicit without repeating long cautions everywhere.

### P1 - visual simplification

- Compact `/study` review and progress cards into secondary summaries.
- Consolidate repeated caution copy into one short note per surface.
- Simplify material and edital list cards to one type/status/action cluster.
- Reduce nested cards, repeated borders, and metric grids where they do not drive action.
- Demote coverage/progress metrics behind the current next step.

### P2 - consistency/responsiveness

- Introduce shared loading/empty/error/needs-review presentation rules.
- Align status labels across material, edital, study, review, and progress surfaces.
- Compress mobile shell/navigation before content.
- Make action groups stack consistently on mobile.
- Review text size/contrast for uppercase microcopy and badges.

### P3 - later enhancements

- Review detail page.
- Richer dashboard composition.
- Progress charts only after semantics justify them.
- Optional animation/motion polish after hierarchy is stable.
- Advanced navigation or command palette after core routes are simplified.

## 12. Proposed implementation slices

### UX-Polish-B: copy cleanup and state-message consolidation

Scope:

- AppShell header/sidebar copy.
- Shared state messages.
- Normal-user terms that still sound internal.
- Repeated caution copy.

Tests:

- Product safety/copy tests.
- Existing navigation/session tests.

Backend changes: none.

### UX-Polish-C: `/study` hierarchy and card-density refinement

Scope:

- `StudySessionWorkspaceClient.tsx`.
- Put next block/study path before review/progress.
- Compact review/progress cards.
- Hide non-actionable not-ready states when blocks exist.

Tests:

- `study-session-workspace.test.tsx`.
- review/progress API tests unchanged.

Backend changes: none.

### UX-Polish-D: block-detail hierarchy and interaction refinement

Scope:

- `StudyBlockDetailReadOnlyClient.tsx`.
- Summary/key points first.
- Objective alternatives rendered once.
- Feedback/reinforcement/caution grouped.
- Progress button placement clarified.

Tests:

- `study-block-detail-page.test.tsx`.
- answer review and progress API tests unchanged.

Backend changes: none.

### UX-Polish-E: materials/editais list and detail simplification

Scope:

- Materials and editais list/detail components.
- Action-first material/detail states.
- Compact classification/status badges.
- Clear edital/material/review distinctions.

Tests:

- materials/editais readonly and safety tests.

Backend changes: none.

### UX-Polish-F: responsive/mobile cleanup

Scope:

- AppShell mobile navigation.
- Study and block detail mobile spacing.
- Card/action wrapping.

Tests:

- Component tests plus browser visual QA.

Backend changes: none.

### UX-Polish-QA-A: final browser visual QA

Scope:

- Desktop, tablet, and mobile pass across login, dashboard, materials, editais, `/study`, and block detail.
- Confirm no forbidden completion/correction/score/gabarito/internal copy.

Backend changes: none.

## 13. Explicit non-goals

No new feature, review detail page, new navigation destination, progress event, material completion, percentage/progress bar, score, answer-key/gabarito, official correction, simulado behavior, OCR/LLM, scheduler, PostgreSQL, provider/signup, backend refactor, or broad visual rebrand belongs in UX-Polish-A or the first polish slices.

## 14. Recommended first implementation phase

Start with `UX-Polish-B: copy cleanup and state-message consolidation`.

Reason:

- It addresses P0 clarity/safety without changing runtime behavior.
- It reduces the cognitive load before layout changes.
- It is easy to verify with existing product-safety, navigation, study, and material/edital tests.
- It creates a cleaner vocabulary foundation for `/study` and block-detail layout refinements.

## UX-Polish-B closeout

UX-Polish-B implemented the first behavior-preserving cleanup slice. It did not change backend behavior, routes, API contracts, progress semantics, review eligibility, or any material completion/correction/scoring capability.

Surfaces cleaned:

- Landing, public navigation, login, AppShell/session notice, dashboard guidance.
- Materials list/detail/upload, edital list/detail, material-step tracking.
- `/study` blocks, cumulative review card, and progress summary card.
- `/study/blocks/[blockId]` header, progress action copy, fixation questions, feedback, and reinforcement.

Copy changes:

- Preferred vocabulary is now more consistent: `Edital`, `Analisar edital`, `Material de estudo`, `Preparar para estudo`, `Seu caminho de estudo`, `Questões de fixação`, `Revisar escolha`, `Feedback`, `Reforço sugerido`, `Acompanhamento do estudo`, and `Revisão acumulada`.
- Old or dense wording such as OCR validation, processing-line language, chunk-like labels, gaps, and long repeated cautions was replaced with product-facing terms such as `Pode exigir conferência`, `Etapas do material`, `partes`, and `pontos a cobrir`.
- Login/auth states now use concise product copy: `Entre para continuar`, `Entrada confirmada. Abrindo seu painel.`, and safe unavailable messages.
- `/study` now uses shorter supporting copy for review and progress states while preserving the safety meaning that review/progress cards do not complete materials or provide scoring.
- Block detail now avoids duplicate objective alternatives and uses one concise feedback caution: `Orientação de estudo, sem correção oficial, notas ou alteração de progresso.`

Remaining work:

- UX-Polish-C should still refine `/study` hierarchy and card density.
- UX-Polish-D should still refine block-detail grouping, spacing, and post-answer hierarchy.
- UX-Polish-E should still simplify materials/editais structure beyond copy-level wording.
- UX-Polish-F should still do responsive/mobile cleanup and browser visual QA.
