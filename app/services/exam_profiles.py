from __future__ import annotations

import unicodedata

from app.domain.models import (
    EditalExtractionResult,
    ExamBoardBehaviorHint,
    ExamCognitiveDemandProfile,
    ExamContentDistributionHint,
    ExamDifficultyProfile,
    ExamProfile,
    ExamProfileSelectionCandidate,
    ExamProfileState,
    ExamProfileSummary,
    ExamProfileWarning,
    ExamQuestionFormatProfile,
    ExamScoringProfile,
    ExamTimingProfile,
)
from app.repositories.json_store import JsonStudyRepository


PROFILE_VERSION = "exam-profiles-v1"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.lower().replace("/", " ").split())


class ExamProfileService:
    def __init__(self, repository: JsonStudyRepository | None = None):
        self.repository = repository
        self._profiles = self._build_profiles()
        self._states = [
            ExamProfileState(
                profile_id=profile.profile_id,
                exam_board=profile.exam_board,
                profile_name=profile.profile_name,
                status="available",
                supported=True,
                metadata={"static_profile": True},
            )
            for profile in self._profiles
        ]

    def list_exam_profiles(self) -> list[ExamProfile]:
        return [item.model_copy(deep=True) for item in self._profiles]

    def list_exam_profile_states(self) -> list[ExamProfileState]:
        return [item.model_copy(deep=True) for item in self._states]

    def get_exam_profile(self, profile_id: str) -> ExamProfile | None:
        for profile in self._profiles:
            if profile.profile_id == profile_id:
                return profile.model_copy(deep=True)
        return None

    def get_exam_profile_for_board(self, board: str) -> ExamProfile | None:
        normalized = _normalize_text(board)
        aliases = {
            "cebraspe": "exam-profile:cebraspe",
            "fgv": "exam-profile:fgv",
            "marinha pscpp": "exam-profile:marinha-pscpp",
            "marinha": "exam-profile:marinha-pscpp",
            "pscpp": "exam-profile:marinha-pscpp",
        }
        profile_id = aliases.get(normalized)
        return self.get_exam_profile(profile_id) if profile_id else None

    def suggest_exam_profile_from_edital(
        self,
        edital_result: EditalExtractionResult | None,
    ) -> ExamProfileSelectionCandidate | None:
        if edital_result is None:
            return None

        signal_text = self._signal_text(edital_result)
        if not signal_text:
            return ExamProfileSelectionCandidate(
                confidence=0.0,
                reasoning=["No stable board signal was found in the available edital artifacts."],
                warnings=[
                    ExamProfileWarning(
                        code="missing_board_signal",
                        message="The edital does not expose enough board-specific wording for a safe suggestion.",
                        severity="warning",
                    )
                ],
                metadata={"edital_id": edital_result.edital_id},
            )

        scores = {
            "exam-profile:cebraspe": self._score_keywords(
                signal_text,
                [
                    "cebraspe",
                    "certo ou errado",
                    "certo errado",
                    "julgue os itens",
                ],
            ),
            "exam-profile:fgv": self._score_keywords(
                signal_text,
                [
                    "fgv",
                    "fundacao getulio vargas",
                    "fundacao getulio",
                    "alternativas a b c d e",
                    "alternativa a",
                ],
            ),
            "exam-profile:marinha-pscpp": self._score_keywords(
                signal_text,
                [
                    "marinha",
                    "pscpp",
                    "praticagem",
                    "autoridade maritima",
                ],
            ),
        }
        highest_score = max(scores.values())
        if highest_score <= 0:
            return None

        top_profiles = [profile_id for profile_id, score in scores.items() if score == highest_score]
        if len(top_profiles) != 1:
            return ExamProfileSelectionCandidate(
                confidence=0.35,
                reasoning=["Multiple board signals were detected with similar strength, so no safe suggestion was selected."],
                warnings=[
                    ExamProfileWarning(
                        code="ambiguous_exam_board_signal",
                        message="The edital contains overlapping board hints and should be reviewed manually.",
                        severity="warning",
                    )
                ],
                metadata={"edital_id": edital_result.edital_id, "candidate_scores": scores},
            )

        selected = self.get_exam_profile(top_profiles[0])
        confidence = min(0.95, round(0.45 + highest_score * 0.12, 2))
        return ExamProfileSelectionCandidate(
            profile_id=selected.profile_id,
            exam_board=selected.exam_board,
            profile_name=selected.profile_name,
            confidence=confidence,
            reasoning=[
                f"Detected edital wording is most consistent with the declarative {selected.profile_name} profile.",
                "This remains a candidate suggestion and does not change runtime behavior automatically.",
            ],
            warnings=[],
            metadata={"edital_id": edital_result.edital_id, "candidate_scores": scores},
        )

    def suggest_exam_profile_for_edital_id(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> ExamProfileSelectionCandidate | None:
        if self.repository is None:
            return None
        edital_result = self.repository.get_edital_extraction_by_id(edital_id, user_id=user_id)
        return self.suggest_exam_profile_from_edital(edital_result)

    def _signal_text(self, edital_result: EditalExtractionResult) -> str:
        parts: list[str] = []
        preview = edital_result.metadata.get("source_text_preview")
        if isinstance(preview, str):
            parts.append(preview)
        for section in edital_result.sections:
            parts.append(section.title)
            parts.append(section.text_excerpt)
        for topic in edital_result.topics:
            parts.append(topic.title)
            parts.append(topic.source_excerpt)
        for hint in edital_result.weight_hints:
            parts.append(hint.target_title)
            parts.append(hint.raw_text)
        return _normalize_text(" ".join(part for part in parts if part))

    def _score_keywords(self, signal_text: str, keywords: list[str]) -> int:
        score = 0
        for keyword in keywords:
            if _normalize_text(keyword) in signal_text:
                score += 1
        return score

    def _build_profiles(self) -> list[ExamProfile]:
        return [
            self._build_cebraspe_profile(),
            self._build_fgv_profile(),
            self._build_marinha_pscpp_profile(),
        ]

    def _build_cebraspe_profile(self) -> ExamProfile:
        return ExamProfile(
            profile_id="exam-profile:cebraspe",
            exam_board="CEBRASPE",
            profile_name="CEBRASPE",
            description="Declarative profile for certo/errado-style objective exams with high wording precision and conceptual traps.",
            question_format=ExamQuestionFormatProfile(
                format_type="true_false",
                expected_question_count=120,
                question_count_range=[80, 150],
                supports_true_false=True,
                supports_multiple_choice=False,
                reasoning="CEBRASPE is conservatively represented as a certo/errado-oriented objective format, but exact counts remain edital-dependent.",
                metadata={"question_count_is_hint": True},
            ),
            timing_profile=ExamTimingProfile(
                total_duration_minutes=210,
                estimated_minutes_per_question=1.75,
                timing_pressure="high",
                reasoning="Reading precision and penalty sensitivity tend to create time pressure even when the exam is fully objective.",
            ),
            scoring_profile=ExamScoringProfile(
                scoring_type="right_wrong",
                penalty_hint=True,
                negative_marking_hint=True,
                partial_credit_hint=False,
                raw_scoring_notes="Negative marking is represented only as a candidate hint and must be confirmed in each edital.",
                reasoning="CEBRASPE commonly uses right/wrong discrimination with penalty-sensitive behavior, but this profile does not treat it as universal law.",
            ),
            content_distribution_hints=[
                ExamContentDistributionHint(
                    hint_id="cebraspe:distribution:precision",
                    distribution_type="priority_hint",
                    value=0.75,
                    source="static_profile",
                    confidence=0.72,
                    reasoning="Precise reading and conceptual discrimination tend to matter across objective blocks.",
                )
            ],
            difficulty_profile=ExamDifficultyProfile(
                default_difficulty="mixed",
                difficulty_distribution={"easy": 0.15, "medium": 0.45, "hard": 0.4},
                expected_variability="high",
                reasoning="The profile assumes mixed difficulty with strong discrimination pressure rather than a flat difficulty curve.",
            ),
            cognitive_demand_profile=ExamCognitiveDemandProfile(
                recall_demand="medium",
                interpretation_demand="high",
                application_demand="medium",
                trap_sensitivity="high",
                time_pressure_sensitivity="high",
                reading_precision_demand="high",
                reasoning="CEBRASPE is modeled as precision-heavy, trap-sensitive and conceptually discriminative.",
            ),
            board_behavior_hints=[
                ExamBoardBehaviorHint(
                    hint_id="cebraspe:behavior:trap",
                    behavior_type="conceptual_trap",
                    description="Careful wording and discriminative alternatives often punish shallow reading.",
                    confidence=0.82,
                    reasoning="Static board hint based on conservative exam-board behavior modeling.",
                ),
                ExamBoardBehaviorHint(
                    hint_id="cebraspe:behavior:precision",
                    behavior_type="eliminatory_precision",
                    description="Minor wording shifts can change the correctness of a statement.",
                    confidence=0.84,
                    reasoning="Static board hint based on conservative exam-board behavior modeling.",
                ),
            ],
            warnings=[
                ExamProfileWarning(
                    code="question_count_is_only_hint",
                    message="The expected question count is only a default hint and must be confirmed by the edital.",
                    severity="info",
                )
            ],
            summary=ExamProfileSummary(
                exam_board="CEBRASPE",
                profile_name="CEBRASPE",
                format_summary="Candidate certo/errado objective profile with strong precision and trap sensitivity.",
                timing_summary="Timing pressure is treated as high because reading precision consumes time.",
                scoring_summary="Penalty-sensitive right/wrong scoring is modeled only as a board-style hint.",
                difficulty_summary="Mixed-to-hard distribution with high conceptual discrimination pressure.",
                cognitive_demand_summary="High reading precision, high trap sensitivity and medium/high interpretation demand.",
                limitation_summary="This profile is declarative only and does not force exact counts, scoring rules or runtime behavior.",
            ),
            metadata={"static_profile": True},
        )

    def _build_fgv_profile(self) -> ExamProfile:
        return ExamProfile(
            profile_id="exam-profile:fgv",
            exam_board="FGV",
            profile_name="FGV",
            description="Declarative profile for multiple-choice objective exams with strong distractors, interpretation and applied reasoning pressure.",
            question_format=ExamQuestionFormatProfile(
                format_type="multiple_choice",
                answer_options=["A", "B", "C", "D", "E"],
                expected_question_count=70,
                question_count_range=[40, 100],
                supports_true_false=False,
                supports_multiple_choice=True,
                reasoning="FGV is conservatively represented as objective multiple-choice with five alternatives, while total counts remain edital-dependent.",
                metadata={"question_count_is_hint": True},
            ),
            timing_profile=ExamTimingProfile(
                total_duration_minutes=240,
                estimated_minutes_per_question=2.5,
                timing_pressure="moderate",
                reasoning="Interpretive reading and distractor evaluation create medium/high pacing pressure in a multiple-choice format.",
            ),
            scoring_profile=ExamScoringProfile(
                scoring_type="multiple_choice",
                penalty_hint=False,
                negative_marking_hint=False,
                partial_credit_hint=False,
                raw_scoring_notes="Exact scoring remains edital-dependent and is not treated as universal.",
                reasoning="FGV is modeled as standard multiple-choice scoring unless the edital states otherwise.",
            ),
            content_distribution_hints=[
                ExamContentDistributionHint(
                    hint_id="fgv:distribution:applied",
                    distribution_type="priority_hint",
                    value=0.7,
                    source="static_profile",
                    confidence=0.7,
                    reasoning="Applied reasoning and distractor filtering tend to matter more than literal recall alone.",
                )
            ],
            difficulty_profile=ExamDifficultyProfile(
                default_difficulty="mixed",
                difficulty_distribution={"easy": 0.2, "medium": 0.5, "hard": 0.3},
                expected_variability="medium",
                reasoning="FGV is modeled as mixed difficulty with frequent interpretation-heavy distractors.",
            ),
            cognitive_demand_profile=ExamCognitiveDemandProfile(
                recall_demand="medium",
                interpretation_demand="high",
                application_demand="high",
                trap_sensitivity="medium",
                time_pressure_sensitivity="medium",
                reading_precision_demand="medium",
                reasoning="FGV is modeled as interpretation- and application-heavy, with meaningful distractor pressure.",
            ),
            board_behavior_hints=[
                ExamBoardBehaviorHint(
                    hint_id="fgv:behavior:interpretive",
                    behavior_type="interpretive_reading",
                    description="Longer stems and nuanced alternatives often demand careful interpretation.",
                    confidence=0.8,
                    reasoning="Static board hint based on conservative exam-board behavior modeling.",
                ),
                ExamBoardBehaviorHint(
                    hint_id="fgv:behavior:applied",
                    behavior_type="applied_problem_solving",
                    description="Applied reasoning and distractor filtering often matter more than isolated memorization.",
                    confidence=0.78,
                    reasoning="Static board hint based on conservative exam-board behavior modeling.",
                ),
            ],
            warnings=[
                ExamProfileWarning(
                    code="question_count_varies_by_edital",
                    message="FGV question count is highly edital-dependent and should not be treated as fixed.",
                    severity="info",
                )
            ],
            summary=ExamProfileSummary(
                exam_board="FGV",
                profile_name="FGV",
                format_summary="Candidate multiple-choice objective profile with five alternatives.",
                timing_summary="Moderate timing pressure driven by interpretation and distractor evaluation.",
                scoring_summary="Standard multiple-choice scoring is assumed unless the edital states otherwise.",
                difficulty_summary="Mixed difficulty with medium/high interpretive load.",
                cognitive_demand_summary="High interpretation and application demand with meaningful distractor sensitivity.",
                limitation_summary="This profile is declarative only and does not force question count, timing or runtime behavior.",
            ),
            metadata={"static_profile": True},
        )

    def _build_marinha_pscpp_profile(self) -> ExamProfile:
        return ExamProfile(
            profile_id="exam-profile:marinha-pscpp",
            exam_board="MARINHA_PSCPP",
            profile_name="Marinha / PSCPP",
            description="Declarative profile for maritime/praticagem-oriented objective exams with technical recall, normative precision and applied operational reasoning.",
            question_format=ExamQuestionFormatProfile(
                format_type="objective",
                answer_options=["A", "B", "C", "D", "E"],
                expected_question_count=70,
                question_count_range=[50, 100],
                supports_true_false=False,
                supports_multiple_choice=True,
                reasoning="Marinha/PSCPP is modeled as an objective technical profile with a conservative question-count range rather than a fixed exam law.",
                metadata={"question_count_is_hint": True, "maritime_context": True},
            ),
            timing_profile=ExamTimingProfile(
                total_duration_minutes=240,
                estimated_minutes_per_question=2.4,
                timing_pressure="moderate",
                reasoning="Technical/normative recall and applied maritime reasoning create edital-dependent pacing, conservatively represented as moderate.",
            ),
            scoring_profile=ExamScoringProfile(
                scoring_type="points_based",
                penalty_hint=False,
                negative_marking_hint=False,
                partial_credit_hint=False,
                raw_scoring_notes="Exact scoring and weight distribution remain edital-dependent.",
                reasoning="The profile keeps scoring broad because maritime selections vary by edital.",
            ),
            content_distribution_hints=[
                ExamContentDistributionHint(
                    hint_id="marinha:distribution:normative",
                    distribution_type="priority_hint",
                    value=0.72,
                    source="static_profile",
                    confidence=0.73,
                    reasoning="Normative detail and operational rules tend to have high practical relevance in maritime technical exams.",
                )
            ],
            difficulty_profile=ExamDifficultyProfile(
                default_difficulty="mixed",
                difficulty_distribution={"easy": 0.2, "medium": 0.45, "hard": 0.35},
                expected_variability="high",
                reasoning="The profile assumes mixed difficulty with technical spikes driven by rules, formulas and operational detail.",
            ),
            cognitive_demand_profile=ExamCognitiveDemandProfile(
                recall_demand="high",
                interpretation_demand="medium",
                application_demand="high",
                trap_sensitivity="medium",
                time_pressure_sensitivity="medium",
                reading_precision_demand="high",
                reasoning="Marinha/PSCPP is modeled as technical/normative recall plus applied maritime reasoning, with strong precision demands.",
            ),
            board_behavior_hints=[
                ExamBoardBehaviorHint(
                    hint_id="marinha:behavior:normative",
                    behavior_type="jurisprudence_or_normative_detail",
                    description="Rules, authorities, operational norms and procedural detail tend to matter.",
                    confidence=0.79,
                    reasoning="Static board hint based on conservative maritime exam behavior modeling.",
                ),
                ExamBoardBehaviorHint(
                    hint_id="marinha:behavior:formula",
                    behavior_type="formula_or_data_recall",
                    description="Technical data, formulas and memorized rule structures may be demanded alongside application.",
                    confidence=0.76,
                    reasoning="Static board hint based on conservative maritime exam behavior modeling.",
                ),
                ExamBoardBehaviorHint(
                    hint_id="marinha:behavior:applied",
                    behavior_type="applied_problem_solving",
                    description="Operational maritime reasoning often appears together with normative recall.",
                    confidence=0.77,
                    reasoning="Static board hint based on conservative maritime exam behavior modeling.",
                ),
            ],
            warnings=[
                ExamProfileWarning(
                    code="pscpp_format_not_fixed",
                    message="Marinha/PSCPP profile is only a conservative default and must be confirmed by the current edital.",
                    severity="info",
                )
            ],
            summary=ExamProfileSummary(
                exam_board="MARINHA_PSCPP",
                profile_name="Marinha / PSCPP",
                format_summary="Candidate maritime-oriented objective profile with edital-dependent question count.",
                timing_summary="Moderate timing pressure with technical and operational reading demands.",
                scoring_summary="Scoring is treated broadly because the edital defines the concrete structure.",
                difficulty_summary="Mixed difficulty with technical spikes from normative and operational detail.",
                cognitive_demand_summary="High recall, high application and high precision demand in maritime/praticagem contexts.",
                limitation_summary="This profile is declarative only and does not hardcode a single PSCPP format or change runtime behavior.",
            ),
            metadata={"static_profile": True, "maritime_context": True},
        )
