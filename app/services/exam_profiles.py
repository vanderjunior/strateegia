from __future__ import annotations

import unicodedata

from app.domain.models import (
    EditalExtractionResult,
    ExamBoardBehaviorHint,
    ExamBoardProfile,
    ExamCognitiveDemandProfile,
    ExamContentBehaviorProfile,
    ExamContentDistributionHint,
    ExamDifficultyProfile,
    ExamGenerationProfile,
    ExamProfile,
    ExamProfileSelectionCandidate,
    ExamProfileState,
    ExamProfileSummary,
    ExamProfileWarning,
    ExamQuestionFormatProfile,
    ExamQuestionStyleProfile,
    ExamScoringProfile,
    ExamTimingProfile,
)
from app.repositories.json_store import JsonStudyRepository


PROFILE_VERSION = "exam-profiles-v1"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.lower().replace("/", " ").replace(",", " ").split())


def _make_warning(code: str, message: str, severity: str = "warning") -> ExamProfileWarning:
    return ExamProfileWarning(code=code, message=message, severity=severity)


def _round_confidence(value: float) -> float:
    return max(0.0, min(1.0, round(value, 2)))


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
            "cespe": "exam-profile:cebraspe",
            "fgv": "exam-profile:fgv",
            "fundacao getulio vargas": "exam-profile:fgv",
            "marinha pscpp": "exam-profile:marinha-pscpp",
            "marinha": "exam-profile:marinha-pscpp",
            "pscpp": "exam-profile:marinha-pscpp",
            "dpc": "exam-profile:marinha-pscpp",
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
                heuristic_confidence=0.0,
                selection_reasoning=["No stable board, family or format signal was found in the available edital artifacts."],
                reasoning=["No stable board, family or format signal was found in the available edital artifacts."],
                warnings=[_make_warning("missing_board_signal", "The edital does not expose enough explicit structure for a safe profile suggestion.")],
                metadata={"edital_id": edital_result.edital_id, "negative_marking_confirmed": False},
            )

        warnings: list[ExamProfileWarning] = []
        family = self._detect_family(signal_text)
        board = self._detect_board(signal_text, include_maritime_board=False)
        format_info = self._detect_format(signal_text)
        scoring = self._detect_scoring(signal_text)

        selected_profile_id: str | None = None
        selected_profile_name: str | None = None
        selected_exam_family: str | None = None
        if family["exam_family"] == "PSCPP":
            selected_profile_id = "exam-profile:marinha-pscpp"
            selected_profile_name = "Marinha / PSCPP"
            selected_exam_family = "PSCPP"
            if board["board_id"] and board["board_id"] != "board:marinha-dpc":
                warnings.append(
                    _make_warning(
                        "exam_family_over_board",
                        "Strong PSCPP/Praticagem family signals took priority over a separate board name while preserving board evidence.",
                    )
                )
        elif board["profile_id"]:
            selected_profile_id = board["profile_id"]
            selected_profile_name = board["profile_name"]

        if board.get("ambiguous"):
            selected_profile_id = None
            selected_profile_name = None
            warnings.append(
                _make_warning(
                    "ambiguous_exam_profile_signals",
                    "Multiple board signals were detected with similar strength, so the board name was not trusted as decisive.",
                )
            )

        if format_info["conflict"]:
            selected_profile_id = None
            selected_profile_name = None
            warnings.append(
                _make_warning(
                    "conflicting_board_and_format",
                    "The edital exposes conflicting explicit format signals and should be reviewed manually before trusting the profile suggestion.",
                )
            )
            warnings.append(
                _make_warning(
                    "ambiguous_exam_profile_signals",
                    "Multiple explicit answer formats were detected with similar strength.",
                )
            )
        elif not format_info["explicit_confirmed"] and board["board_id"]:
            warnings.append(
                _make_warning(
                    "format_requires_confirmation",
                    "The exam board was detected, but the explicit answer format still needs edital confirmation.",
                    severity="info",
                )
            )
            warnings.append(
                _make_warning(
                    "board_style_used_as_fallback",
                    "Board style was used only as a fallback hint because the edital did not confirm the answer format explicitly.",
                    severity="info",
                )
            )

        if format_info["discursive_module"]:
            warnings.append(
                _make_warning(
                    "discursive_module_detected",
                    "Discursive wording was detected, so the answer format should be treated as mixed/discursive candidate behavior.",
                    severity="info",
                )
            )

        selection_reasoning = []
        if selected_exam_family == "PSCPP":
            selection_reasoning.append("Special exam-family/domain signals were prioritized over generic board defaults.")
        if format_info["explicit_confirmed"]:
            selection_reasoning.append("Explicit edital format wording was prioritized over board default assumptions.")
        elif board["board_id"]:
            selection_reasoning.append("Board style remains only a fallback hint because the edital format is not explicit.")
        if scoring["explicit_confirmed"]:
            selection_reasoning.append("Scoring hints were attached only because explicit scoring wording was found.")

        confidence_components = [
            family["confidence"],
            format_info["confidence"],
            board["confidence"],
            scoring["confidence"],
        ]
        available_components = [item for item in confidence_components if item > 0]
        final_confidence = _round_confidence(sum(available_components) / len(available_components)) if available_components else 0.0

        if selected_profile_id is None and format_info["format_type"] == "unknown" and board["board_id"] is None and family["exam_family"] is None and scoring["confidence"] <= 0.2:
            return ExamProfileSelectionCandidate(
                confidence=0.0,
                heuristic_confidence=0.0,
                format_type="unknown",
                selection_reasoning=["The edital does not provide enough explicit board, family or format evidence for a safe suggestion."],
                reasoning=["The edital does not provide enough explicit board, family or format evidence for a safe suggestion."],
                warnings=warnings or [_make_warning("missing_board_signal", "No stable exam-board or format signal was found.")],
                metadata={"edital_id": edital_result.edital_id, "negative_marking_confirmed": False},
            )

        return ExamProfileSelectionCandidate(
            profile_id=selected_profile_id,
            board_id=board["board_id"],
            exam_board=board["board_name"],
            profile_name=selected_profile_name,
            exam_family=selected_exam_family,
            format_type=format_info["format_type"],
            confidence=final_confidence if not format_info["conflict"] else min(0.5, final_confidence or 0.35),
            heuristic_confidence=final_confidence,
            format_confidence=format_info["confidence"],
            board_confidence=board["confidence"],
            family_confidence=family["confidence"],
            scoring_confidence=scoring["confidence"],
            reasoning=selection_reasoning or ["Candidate profile suggestion remained conservative and declarative."],
            selection_reasoning=selection_reasoning or ["Candidate profile suggestion remained conservative and declarative."],
            format_evidence=format_info["evidence"],
            scoring_evidence=scoring["evidence"],
            family_evidence=family["evidence"],
            board_evidence=board["evidence"],
            warnings=warnings,
            metadata={
                "edital_id": edital_result.edital_id,
                "negative_marking_confirmed": scoring["negative_marking_confirmed"],
                "format_source": format_info["source"],
                "format_requires_confirmation": not format_info["explicit_confirmed"],
            },
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

    def _match_keywords(self, signal_text: str, pairs: list[tuple[str, str]]) -> list[str]:
        matches: list[str] = []
        for keyword, evidence in pairs:
            normalized_keyword = _normalize_text(keyword)
            if self._contains_non_negated_keyword(signal_text, normalized_keyword) and evidence not in matches:
                matches.append(evidence)
        return matches

    def _contains_non_negated_keyword(self, signal_text: str, normalized_keyword: str) -> bool:
        search_start = 0
        while True:
            index = signal_text.find(normalized_keyword, search_start)
            if index < 0:
                return False
            prefix = signal_text[max(0, index - 48):index]
            if not any(marker in prefix for marker in [" sem ", " sem referencia a ", " sem mencao a ", " nao "]):
                return True
            search_start = index + len(normalized_keyword)

    def _detect_family(self, signal_text: str) -> dict[str, object]:
        evidence = self._match_keywords(
            signal_text,
            [
                ("pscpp", "PSCPP"),
                ("praticante de pratico", "Praticante de Pratico"),
                ("servico de praticagem", "Servico de Praticagem"),
                ("normam 311", "NORMAM-311"),
                ("normam-311", "NORMAM-311"),
                ("diretoria de portos e costas", "Diretoria de Portos e Costas"),
                ("dpc", "DPC"),
                ("autoridade maritima", "Autoridade Maritima"),
                ("praticagem", "Praticagem"),
            ],
        )
        confidence = 0.0
        exam_family = None
        if evidence:
            exam_family = "PSCPP"
            confidence = 0.95 if any(item in {"PSCPP", "Praticagem", "NORMAM-311"} for item in evidence) else 0.75
        return {"exam_family": exam_family, "confidence": confidence, "evidence": evidence}

    def _detect_board(self, signal_text: str, *, include_maritime_board: bool = True) -> dict[str, object]:
        candidates = [
            {
                "board_id": "board:cebraspe",
                "board_name": "CEBRASPE",
                "profile_id": "exam-profile:cebraspe",
                "profile_name": "CEBRASPE",
                "keywords": [("cebraspe", "CEBRASPE"), ("cespe", "CESPE")],
            },
            {
                "board_id": "board:fgv",
                "board_name": "FGV",
                "profile_id": "exam-profile:fgv",
                "profile_name": "FGV",
                "keywords": [("fgv", "FGV"), ("fundacao getulio vargas", "Fundacao Getulio Vargas"), ("fundacao getulio", "Fundacao Getulio")],
            },
            {
                "board_id": "board:quadrix",
                "board_name": "QUADRIX",
                "profile_id": None,
                "profile_name": None,
                "keywords": [("quadrix", "Quadrix")],
            },
            {
                "board_id": "board:ibfc",
                "board_name": "IBFC",
                "profile_id": None,
                "profile_name": None,
                "keywords": [("ibfc", "IBFC")],
            },
            {
                "board_id": "board:aocp",
                "board_name": "AOCP",
                "profile_id": None,
                "profile_name": None,
                "keywords": [("instituto aocp", "Instituto AOCP"), ("aocp", "AOCP")],
            },
        ]
        if include_maritime_board:
            candidates.append(
                {
                    "board_id": "board:marinha-dpc",
                    "board_name": "MARINHA_DPC",
                    "profile_id": "exam-profile:marinha-pscpp",
                    "profile_name": "Marinha / PSCPP",
                    "keywords": [("marinha", "Marinha"), ("diretoria de portos e costas", "Diretoria de Portos e Costas"), ("dpc", "DPC")],
                }
            )
        best = {"board_id": None, "board_name": None, "profile_id": None, "profile_name": None, "confidence": 0.0, "evidence": [], "ambiguous": False}
        matched_candidates: list[dict[str, object]] = []
        for candidate in candidates:
            evidence = self._match_keywords(signal_text, candidate["keywords"])
            if evidence:
                matched_candidates.append(
                    {
                        "board_id": candidate["board_id"],
                        "board_name": candidate["board_name"],
                        "profile_id": candidate["profile_id"],
                        "profile_name": candidate["profile_name"],
                        "confidence": 0.8 if len(evidence) >= 2 else 0.6,
                        "evidence": evidence,
                    }
                )
            if evidence and len(evidence) > len(best["evidence"]):
                best = {
                    "board_id": candidate["board_id"],
                    "board_name": candidate["board_name"],
                    "profile_id": candidate["profile_id"],
                    "profile_name": candidate["profile_name"],
                    "confidence": 0.8 if len(evidence) >= 2 else 0.6,
                    "evidence": evidence,
                    "ambiguous": False,
                }
        if matched_candidates:
            max_count = max(len(item["evidence"]) for item in matched_candidates)
            top = [item for item in matched_candidates if len(item["evidence"]) == max_count]
            if len(top) > 1:
                return {
                    "board_id": None,
                    "board_name": None,
                    "profile_id": None,
                    "profile_name": None,
                    "confidence": 0.35,
                    "evidence": sorted({evidence for item in top for evidence in item["evidence"]}),
                    "ambiguous": True,
                }
        return best

    def _detect_format(self, signal_text: str) -> dict[str, object]:
        true_false_evidence = self._match_keywords(
            signal_text,
            [
                ("certo ou errado", "Certo ou Errado"),
                ("julgue os itens", "Julgue os Itens"),
                ("campo c", "Campo C"),
                ("campo e", "Campo E"),
            ],
        )
        multiple_choice_5_evidence = self._match_keywords(
            signal_text,
            [
                ("a b c d e", "A, B, C, D, E"),
                ("cinco alternativas", "Cinco alternativas"),
                ("5 alternativas", "5 alternativas"),
            ],
        )
        multiple_choice_4_evidence = self._match_keywords(
            signal_text,
            [
                ("a b c d", "A, B, C, D"),
                ("quatro alternativas", "Quatro alternativas"),
                ("4 alternativas", "4 alternativas"),
            ],
        )
        if multiple_choice_5_evidence and "A, B, C, D" in multiple_choice_4_evidence:
            multiple_choice_4_evidence = [item for item in multiple_choice_4_evidence if item != "A, B, C, D"]
        discursive_evidence = self._match_keywords(
            signal_text,
            [
                ("questoes discursivas", "Questoes discursivas"),
                ("questao discursiva", "Questao discursiva"),
                ("folha de textos definitivos", "Folha de Textos Definitivos"),
                ("texto definitivo", "Texto definitivo"),
                ("etapa discursiva", "Etapa discursiva"),
            ],
        )
        oral_evidence = self._match_keywords(
            signal_text,
            [
                ("prova oral", "Prova oral"),
                ("avaliacao oral", "Avaliacao oral"),
            ],
        )

        explicit_formats = []
        if true_false_evidence:
            explicit_formats.append("true_false")
        if multiple_choice_5_evidence:
            explicit_formats.append("multiple_choice_5")
        if multiple_choice_4_evidence:
            explicit_formats.append("multiple_choice_4")
        if discursive_evidence:
            explicit_formats.append("discursive")
        if oral_evidence:
            explicit_formats.append("oral")

        if len([item for item in explicit_formats if item in {"true_false", "multiple_choice_5", "multiple_choice_4"}]) > 1:
            return {
                "format_type": "unknown",
                "confidence": 0.25,
                "evidence": true_false_evidence + multiple_choice_5_evidence + multiple_choice_4_evidence,
                "explicit_confirmed": False,
                "source": "conflicting_explicit_signals",
                "conflict": True,
                "discursive_module": bool(discursive_evidence),
            }

        if oral_evidence:
            return {
                "format_type": "oral",
                "confidence": 0.9,
                "evidence": oral_evidence,
                "explicit_confirmed": True,
                "source": "explicit_edital_signal",
                "conflict": False,
                "discursive_module": False,
            }
        if discursive_evidence and (multiple_choice_5_evidence or multiple_choice_4_evidence):
            return {
                "format_type": "mixed",
                "confidence": 0.85,
                "evidence": (multiple_choice_5_evidence or multiple_choice_4_evidence) + discursive_evidence,
                "explicit_confirmed": True,
                "source": "explicit_edital_signal",
                "conflict": False,
                "discursive_module": True,
            }
        if discursive_evidence:
            return {
                "format_type": "discursive",
                "confidence": 0.82,
                "evidence": discursive_evidence,
                "explicit_confirmed": True,
                "source": "explicit_edital_signal",
                "conflict": False,
                "discursive_module": True,
            }
        if true_false_evidence:
            return {
                "format_type": "true_false",
                "confidence": 0.9,
                "evidence": true_false_evidence,
                "explicit_confirmed": True,
                "source": "explicit_edital_signal",
                "conflict": False,
                "discursive_module": False,
            }
        if multiple_choice_5_evidence:
            return {
                "format_type": "multiple_choice_5",
                "confidence": 0.88,
                "evidence": multiple_choice_5_evidence,
                "explicit_confirmed": True,
                "source": "explicit_edital_signal",
                "conflict": False,
                "discursive_module": False,
            }
        if multiple_choice_4_evidence:
            return {
                "format_type": "multiple_choice_4",
                "confidence": 0.88,
                "evidence": multiple_choice_4_evidence,
                "explicit_confirmed": True,
                "source": "explicit_edital_signal",
                "conflict": False,
                "discursive_module": False,
            }
        return {
            "format_type": "unknown",
            "confidence": 0.0,
            "evidence": [],
            "explicit_confirmed": False,
            "source": "unknown",
            "conflict": False,
            "discursive_module": False,
        }

    def _detect_scoring(self, signal_text: str) -> dict[str, object]:
        evidence = self._match_keywords(
            signal_text,
            [
                ("ponto negativo", "ponto negativo"),
                ("1 00 ponto negativo", "1,00 ponto negativo"),
                ("-1", "-1"),
                ("em branco", "em branco"),
                ("zero ponto", "zero ponto"),
                ("dupla marcacao", "dupla marcacao"),
                ("discordancia com o gabarito", "discordancia com o gabarito"),
            ],
        )
        negative_marking_confirmed = any(item in {"ponto negativo", "1,00 ponto negativo", "-1", "discordancia com o gabarito"} for item in evidence)
        confidence = 0.88 if negative_marking_confirmed else (0.55 if evidence else 0.2)
        return {
            "evidence": evidence,
            "negative_marking_confirmed": negative_marking_confirmed,
            "explicit_confirmed": bool(evidence),
            "confidence": confidence if evidence else 0.2,
        }

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
            board_profile=ExamBoardProfile(
                board_id="board:cebraspe",
                board_name="CEBRASPE",
                aliases=["CEBRASPE", "CESPE"],
                default_style_hints=["precision_heavy", "assertion_discrimination", "trap_sensitive"],
                warnings=["confirm explicit format in edital", "confirm negative marking in edital"],
            ),
            exam_family="generic",
            description="Declarative board-style profile for CEBRASPE with precision-heavy wording, conceptual traps and non-authoritative default hints.",
            question_format=ExamQuestionFormatProfile(
                format_type="unknown",
                expected_question_count=120,
                question_count_range=[80, 150],
                format_source="board_default",
                format_confidence=0.35,
                explicit_format_confirmed=False,
                supports_true_false=True,
                supports_multiple_choice=True,
                supports_discursive=False,
                reasoning="CEBRASPE board style does not by itself force certo/errado; explicit edital wording should confirm the real answer format.",
                metadata={"question_count_is_hint": True},
            ),
            timing_profile=ExamTimingProfile(
                total_duration_minutes=210,
                estimated_minutes_per_question=1.75,
                timing_pressure="high",
                reasoning="Reading precision and conceptual discrimination often create high timing pressure.",
            ),
            scoring_profile=ExamScoringProfile(
                scoring_type="right_wrong",
                negative_marking=False,
                penalty_hint=True,
                negative_marking_hint=True,
                scoring_source="board_default",
                explicit_scoring_confirmed=False,
                scoring_confidence=0.35,
                raw_scoring_notes="Negative marking must be confirmed by the edital and is not treated as universal truth from the board name alone.",
                reasoning="Penalty-sensitive scoring is kept only as historical/default hint until explicit scoring language appears in the edital.",
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
                reasoning="The profile assumes mixed difficulty with strong discrimination pressure.",
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
            generation_profile=ExamGenerationProfile(
                generation_style="assertion_based",
                stem_style="assertive",
                distractor_quality="n/a",
                trap_patterns=[
                    "necessary_vs_sufficient_swap",
                    "always_never_generalization",
                    "exception_as_rule",
                    "concept_mixing",
                    "normative_detail",
                    "partially_correct_statement_with_false_clause",
                ],
                command_patterns=["julgue os itens", "certo ou errado"],
                reasoning="Future-generation hint only; no question generation is activated here.",
            ),
            question_style_profile=ExamQuestionStyleProfile(
                stem_length="medium",
                contextualization="medium",
                literalness="medium",
                case_based="low",
                technical_depth="medium",
                distractor_similarity="n/a",
                reading_precision="high",
                technical_language="medium",
                reasoning="Question-style hints remain declarative and conservative.",
            ),
            content_behavior_profile=ExamContentBehaviorProfile(
                law_dry_text_weight="medium",
                jurisprudence_weight="medium",
                doctrine_weight="low",
                calculation_weight="low",
                technical_standard_weight="medium",
                bibliography_weight="low",
                case_problem_weight="medium",
                normative_detail_weight="high",
                technical_operational_weight="low",
            ),
            board_behavior_hints=[
                ExamBoardBehaviorHint(
                    hint_id="cebraspe:behavior:trap",
                    behavior_type="conceptual_trap",
                    description="Careful wording often punishes shallow reading and partially correct assertions.",
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
                _make_warning("question_count_is_only_hint", "The expected question count is only a default hint and must be confirmed by the edital.", "info"),
                _make_warning("confirm_ce_format_in_edital", "Do not assume certo/errado format only from the CEBRASPE name.", "info"),
                _make_warning("confirm_negative_marking_in_edital", "Do not assume penalty/negative marking only from the CEBRASPE name.", "info"),
            ],
            summary=ExamProfileSummary(
                exam_board="CEBRASPE",
                profile_name="CEBRASPE",
                format_summary="Board-style profile separated from explicit answer format; edital confirmation still decides the actual format.",
                timing_summary="Timing pressure is treated as high because precise reading and conceptual discrimination consume time.",
                scoring_summary="Penalty-sensitive scoring remains only a candidate hint until the edital confirms it.",
                difficulty_summary="Mixed-to-hard distribution with high discrimination pressure.",
                cognitive_demand_summary="High reading precision, high trap sensitivity and medium/high interpretation demand.",
                limitation_summary="This profile is declarative only and does not force certo/errado, scoring rules or runtime behavior.",
            ),
            metadata={"static_profile": True},
        )

    def _build_fgv_profile(self) -> ExamProfile:
        return ExamProfile(
            profile_id="exam-profile:fgv",
            exam_board="FGV",
            profile_name="FGV",
            board_profile=ExamBoardProfile(
                board_id="board:fgv",
                board_name="FGV",
                aliases=["FGV", "Fundacao Getulio Vargas"],
                default_style_hints=["multiple_choice_common", "interpretive", "distractor_sensitive"],
                warnings=["confirm number of alternatives in edital", "explicit format prevails over board style"],
            ),
            exam_family="generic",
            description="Declarative board-style profile for FGV with interpretation-heavy stems, applied reasoning and high distractor similarity.",
            question_format=ExamQuestionFormatProfile(
                format_type="multiple_choice_5",
                options_count=5,
                answer_options=["A", "B", "C", "D", "E"],
                expected_question_count=70,
                question_count_range=[40, 100],
                single_correct_answer=True,
                format_source="board_default",
                format_confidence=0.55,
                explicit_format_confirmed=False,
                supports_true_false=False,
                supports_multiple_choice=True,
                supports_discursive=True,
                reasoning="FGV commonly uses five-option objective items, but the edital should still confirm the exact alternative count and whether a discursive module exists.",
                metadata={"question_count_is_hint": True},
            ),
            timing_profile=ExamTimingProfile(
                total_duration_minutes=240,
                estimated_minutes_per_question=2.5,
                timing_pressure="moderate",
                reasoning="Interpretive reading and distractor evaluation create medium/high pacing pressure.",
            ),
            scoring_profile=ExamScoringProfile(
                scoring_type="multiple_choice",
                penalty_hint=False,
                negative_marking_hint=False,
                scoring_source="board_default",
                explicit_scoring_confirmed=False,
                scoring_confidence=0.4,
                raw_scoring_notes="Exact scoring remains edital-dependent.",
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
                reasoning="FGV is modeled as mixed difficulty with strong interpretive load.",
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
            generation_profile=ExamGenerationProfile(
                generation_style="interpretive",
                stem_style="contextualized",
                distractor_quality="high",
                trap_patterns=["close_alternatives", "interpretive_shift", "applied_detail_swap"],
                command_patterns=["assinale a alternativa correta", "marque a alternativa incorreta"],
                reasoning="Future-generation hint only; no question generation is activated here.",
            ),
            question_style_profile=ExamQuestionStyleProfile(
                stem_length="medium",
                contextualization="high",
                literalness="medium",
                case_based="high",
                technical_depth="medium",
                distractor_similarity="high",
                reading_precision="medium",
                technical_language="medium",
                reasoning="FGV style hints emphasize contextualized stems and close alternatives.",
            ),
            content_behavior_profile=ExamContentBehaviorProfile(
                law_dry_text_weight="medium",
                jurisprudence_weight="medium",
                doctrine_weight="medium",
                calculation_weight="low",
                technical_standard_weight="medium",
                bibliography_weight="low",
                case_problem_weight="high",
                normative_detail_weight="medium",
                technical_operational_weight="medium",
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
                _make_warning("question_count_varies_by_edital", "FGV question count is highly edital-dependent and should not be treated as fixed.", "info"),
                _make_warning("confirm_option_count_in_edital", "Confirm the number of alternatives in the edital before treating FGV as fixed A/B/C/D/E.", "info"),
                _make_warning("board_style_does_not_override_explicit_format", "FGV board style must not override explicit edital answer-format wording.", "info"),
                _make_warning("discursive_module_requires_edital_signal", "A discursive module should only be assumed when the edital states it explicitly.", "info"),
            ],
            summary=ExamProfileSummary(
                exam_board="FGV",
                profile_name="FGV",
                format_summary="Common five-option multiple-choice board style, still subordinate to explicit edital format wording.",
                timing_summary="Moderate timing pressure driven by interpretation and distractor evaluation.",
                scoring_summary="Standard multiple-choice scoring is assumed only as a fallback hint.",
                difficulty_summary="Mixed difficulty with medium/high interpretive load.",
                cognitive_demand_summary="High interpretation and application demand with high distractor similarity.",
                limitation_summary="This profile is declarative only and does not force alternative count, discursive modules or runtime behavior.",
            ),
            metadata={"static_profile": True},
        )

    def _build_marinha_pscpp_profile(self) -> ExamProfile:
        return ExamProfile(
            profile_id="exam-profile:marinha-pscpp",
            exam_board="MARINHA_PSCPP",
            profile_name="Marinha / PSCPP",
            board_profile=ExamBoardProfile(
                board_id="board:marinha-dpc",
                board_name="MARINHA_DPC",
                aliases=["Marinha", "DPC", "Diretoria de Portos e Costas"],
                default_style_hints=["technical_maritime", "bibliography_driven", "normative_operational"],
                warnings=["PSCPP is not a generic military exam", "exam family may prevail over external board mention"],
            ),
            exam_family="PSCPP",
            description="Declarative special-family profile for PSCPP/Praticagem with technical-operational maritime focus, official bibliography priority and normative precision.",
            question_format=ExamQuestionFormatProfile(
                format_type="objective",
                options_count=0,
                answer_options=["A", "B", "C", "D", "E"],
                expected_question_count=70,
                question_count_range=[50, 100],
                single_correct_answer=True,
                format_source="board_default",
                format_confidence=0.4,
                explicit_format_confirmed=False,
                supports_true_false=False,
                supports_multiple_choice=True,
                supports_discursive=False,
                reasoning="PSCPP/Praticagem is modeled as objective and technical, but the real answer format still depends on explicit edital wording.",
                metadata={"question_count_is_hint": True, "maritime_context": True},
            ),
            timing_profile=ExamTimingProfile(
                total_duration_minutes=240,
                estimated_minutes_per_question=2.4,
                timing_pressure="moderate",
                reasoning="Technical/normative recall and applied maritime reasoning create edital-dependent pacing.",
            ),
            scoring_profile=ExamScoringProfile(
                scoring_type="points_based",
                scoring_source="unknown",
                explicit_scoring_confirmed=False,
                scoring_confidence=0.2,
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
                reasoning="PSCPP is modeled as technical/normative recall plus applied maritime reasoning.",
            ),
            generation_profile=ExamGenerationProfile(
                generation_style="technical_maritime",
                stem_style="technical_operational",
                distractor_quality="medium",
                trap_patterns=["normative_detail", "operational_exception", "formula_data_confusion"],
                command_patterns=["analise a situacao operacional", "assinale a alternativa correta"],
                allow_english_terms=True,
                allow_multitopic_items=True,
                reasoning="Future-generation hint only; no question generation is activated here.",
            ),
            question_style_profile=ExamQuestionStyleProfile(
                stem_length="medium",
                contextualization="high",
                literalness="medium",
                case_based="medium",
                technical_depth="high",
                distractor_similarity="medium",
                reading_precision="high",
                technical_language="high",
                reasoning="PSCPP style hints emphasize maritime technical language and operational detail.",
            ),
            content_behavior_profile=ExamContentBehaviorProfile(
                law_dry_text_weight="medium",
                jurisprudence_weight="low",
                doctrine_weight="low",
                calculation_weight="medium",
                technical_standard_weight="high",
                bibliography_weight="high",
                case_problem_weight="medium",
                normative_detail_weight="high",
                technical_operational_weight="high",
            ),
            board_behavior_hints=[
                ExamBoardBehaviorHint(
                    hint_id="marinha:behavior:normative",
                    behavior_type="jurisprudence_or_normative_detail",
                    description="Rules, authorities, operational norms and procedural detail tend to matter.",
                    confidence=0.79,
                    reasoning="Static maritime-family hint based on conservative exam behavior modeling.",
                ),
                ExamBoardBehaviorHint(
                    hint_id="marinha:behavior:formula",
                    behavior_type="formula_or_data_recall",
                    description="Technical data, formulas and memorized rule structures may be demanded alongside application.",
                    confidence=0.76,
                    reasoning="Static maritime-family hint based on conservative exam behavior modeling.",
                ),
                ExamBoardBehaviorHint(
                    hint_id="marinha:behavior:applied",
                    behavior_type="applied_problem_solving",
                    description="Operational maritime reasoning often appears together with normative recall.",
                    confidence=0.77,
                    reasoning="Static maritime-family hint based on conservative exam behavior modeling.",
                ),
            ],
            warnings=[
                _make_warning("pscpp_not_generic_military_exam", "Do not treat PSCPP/Praticagem as a generic military exam.", "info"),
                _make_warning("exam_family_over_board_when_needed", "PSCPP/Praticagem family signals should prevail over generic board defaults when strongly present.", "info"),
                _make_warning("pscpp_format_not_fixed", "The actual answer format still depends on the edital and should not be hardcoded.", "info"),
            ],
            summary=ExamProfileSummary(
                exam_board="MARINHA_PSCPP",
                profile_name="Marinha / PSCPP",
                format_summary="Special-family maritime profile separated from explicit answer format and answer-option count.",
                timing_summary="Moderate timing pressure with technical and operational reading demands.",
                scoring_summary="Scoring remains edital-dependent and is not assumed from family or board name alone.",
                difficulty_summary="Mixed difficulty with technical spikes from normative and operational detail.",
                cognitive_demand_summary="High recall, high application and high precision demand in maritime/praticagem contexts.",
                limitation_summary="This profile is declarative only and does not hardcode a single PSCPP format or change runtime behavior.",
            ),
            metadata={"static_profile": True, "maritime_context": True},
        )
