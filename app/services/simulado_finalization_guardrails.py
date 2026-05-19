from __future__ import annotations

from app.domain.models import (
    CandidateFinalizationSummary,
    FinalizationBlocker,
    FinalizationValidationFinding,
    FinalizationWarning,
    SimuladoAttemptShell,
    SimuladoFinalizationGuardrail,
    SimuladoQuestionAssembly,
    SimuladoQuestionCandidate,
)
from app.repositories.json_store import JsonStudyRepository


FINALIZATION_GUARDRAIL_BUILD_METHOD = "heuristic_simulado_finalization_guardrails_builder"


class SimuladoFinalizationGuardrailsService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_guardrail(
        self,
        source_attempt_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalizationGuardrail | None:
        if user_id is None:
            return None
        existing = self.repository.get_simulado_finalization_guardrail(
            source_attempt_shell_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        attempt_shell = self.repository.get_simulado_attempt_shell_by_id(
            source_attempt_shell_id,
            user_id=user_id,
        )
        if attempt_shell is None:
            return None

        assembly = self.repository.get_simulado_question_assembly_by_id(
            attempt_shell.source_assembly_id,
            user_id=user_id,
        )
        if assembly is None:
            return None

        candidate_summaries = [
            self._candidate_summary(candidate, assembly)
            for candidate in assembly.candidates
        ]
        blockers = self._build_blockers(assembly, attempt_shell)
        validation_findings = self._build_findings(assembly, attempt_shell)
        warnings = self._build_warnings(assembly, attempt_shell)
        status, readiness_state = self._guardrail_state(assembly, attempt_shell)

        total_candidates = assembly.total_candidates
        missing_final_questions_count = total_candidates if assembly.no_final_questions_created else 0
        missing_final_answer_keys_count = total_candidates if assembly.no_final_answer_keys_created else 0
        missing_final_explanations_count = total_candidates if assembly.no_final_explanations_created else 0

        result = SimuladoFinalizationGuardrail(
            finalization_guardrail_id=f"simulado-finalization-guardrail:{source_attempt_shell_id}",
            user_id=user_id,
            source_assembly_id=assembly.assembly_id,
            source_attempt_shell_id=source_attempt_shell_id,
            source_simulado_blueprint_id=assembly.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_candidates=total_candidates,
            review_ready_candidates=attempt_shell.review_ready_candidates,
            blocked_candidates=attempt_shell.blocked_candidates,
            needs_review_candidates=attempt_shell.needs_review_candidates,
            finalizable_candidates_count=0,
            approved_candidates_count=0,
            missing_final_questions_count=missing_final_questions_count,
            missing_final_answer_keys_count=missing_final_answer_keys_count,
            missing_final_explanations_count=missing_final_explanations_count,
            candidate_summaries=candidate_summaries,
            blockers=blockers,
            validation_findings=validation_findings,
            warnings=warnings,
            approval_required=True,
            human_review_required=True,
            execution_enabled=False,
            correction_enabled=False,
            scoring_enabled=False,
            student_submission_enabled=False,
            progress_mutation_enabled=False,
            no_student_attempt_created=True,
            no_answer_submission_enabled=True,
            no_correction_result_created=True,
            no_score_created=True,
            metadata={
                "build_method": FINALIZATION_GUARDRAIL_BUILD_METHOD,
                "assembly_status": assembly.status,
                "assembly_readiness_state": assembly.readiness_state,
                "attempt_shell_status": attempt_shell.status,
                "attempt_shell_readiness_state": attempt_shell.readiness_state,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_finalization_guardrail(result, user_id=user_id)
        return result

    def get_guardrail(
        self,
        source_attempt_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalizationGuardrail | None:
        return self.repository.get_simulado_finalization_guardrail(
            source_attempt_shell_id,
            user_id=user_id,
        )

    def get_guardrail_by_id(
        self,
        finalization_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalizationGuardrail | None:
        return self.repository.get_simulado_finalization_guardrail_by_id(
            finalization_guardrail_id,
            user_id=user_id,
        )

    def _guardrail_state(
        self,
        assembly: SimuladoQuestionAssembly,
        attempt_shell: SimuladoAttemptShell,
    ) -> tuple[str, str]:
        if assembly.total_candidates == 0 or attempt_shell.review_ready_candidates == 0:
            return "finalization_not_available", "blocked_by_insufficient_candidates"
        if any(
            item.readiness_state == "candidate_blocked_by_unsupported_format"
            for item in assembly.candidates
        ):
            return "finalization_blocked", "blocked_by_unsupported_format"
        if attempt_shell.execution_enabled is False:
            return "finalization_blocked", "blocked_by_attempt_shell_not_executable"
        if assembly.not_executable:
            return "finalization_blocked", "blocked_by_non_final_assembly"
        if (
            assembly.no_final_questions_created
            or assembly.no_final_answer_keys_created
            or assembly.no_final_explanations_created
            or assembly.requires_human_review
            or attempt_shell.requires_human_finalization
        ):
            return "finalization_needs_review", "needs_human_approval_review"
        return "finalization_ready_for_human_approval_review", "ready_for_future_approval_review"

    def _candidate_summary(
        self,
        candidate: SimuladoQuestionCandidate,
        assembly: SimuladoQuestionAssembly,
    ) -> CandidateFinalizationSummary:
        blockers: list[str] = []
        warnings: list[str] = []

        mapped_state = "candidate_finalization_blocked"
        if candidate.readiness_state == "candidate_blocked_by_unsupported_format":
            mapped_state = "candidate_blocked_by_unsupported_format"
            blockers.append("candidate_blocked_by_unsupported_format")
        elif candidate.readiness_state == "candidate_blocked_by_non_reviewed_draft":
            mapped_state = "candidate_blocked_by_unreviewed_draft"
            blockers.append("candidate_blocked_by_unreviewed_draft")
        elif candidate.readiness_state in {
            "candidate_blocked_by_source_issue",
            "candidate_blocked_by_ocr",
            "candidate_blocked_by_material_gap",
        }:
            mapped_state = "candidate_blocked_by_source_issue"
            blockers.append("candidate_blocked_by_source_issue")
        elif candidate.readiness_state in {
            "candidate_blocked_by_unfinalized_answer",
            "candidate_blocked_by_missing_guardrail",
        }:
            mapped_state = "candidate_blocked_by_unfinalized_guardrail"
            blockers.append("candidate_blocked_by_unfinalized_guardrail")
        elif candidate.readiness_state == "candidate_needs_review":
            mapped_state = "candidate_needs_human_review"
            warnings.append("candidate_needs_human_review")
        else:
            mapped_state = "candidate_blocked_by_missing_final_question"

        if assembly.no_final_questions_created:
            blockers.append("candidate_blocked_by_missing_final_question")
        if assembly.no_final_answer_keys_created:
            blockers.append("candidate_blocked_by_missing_final_answer_key")
        if assembly.no_final_explanations_created:
            blockers.append("candidate_blocked_by_missing_final_explanation")
        if candidate.readiness_state == "candidate_ready_for_review":
            warnings.append("review_ready_not_finalizable")

        blockers = sorted(set(blockers))
        warnings = sorted(set(warnings))

        return CandidateFinalizationSummary(
            candidate_id=f"finalization-summary:{candidate.candidate_id}",
            source_question_candidate_id=candidate.candidate_id,
            source_question_draft_id=candidate.source_question_draft_id,
            source_guardrail_id=candidate.source_guardrail_id,
            readiness_state=mapped_state,
            review_required=True,
            finalization_blocked=True,
            has_final_question=False,
            has_final_answer_key=False,
            has_final_explanation=False,
            approval_state="approval_required",
            blockers=blockers,
            warnings=warnings,
            metadata={
                "candidate_readiness_state": candidate.readiness_state,
                "not_executable": candidate.not_executable,
                "not_scoreable": candidate.not_scoreable,
            },
        )

    def _build_blockers(
        self,
        assembly: SimuladoQuestionAssembly,
        attempt_shell: SimuladoAttemptShell,
    ) -> list[FinalizationBlocker]:
        blockers: list[FinalizationBlocker] = []
        if assembly.not_executable:
            blockers.append(
                self._blocker(
                    "blocked_by_non_final_assembly",
                    "Simulado question assembly remains non-final and non-executable in this pass.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if attempt_shell.execution_enabled is False:
            blockers.append(
                self._blocker(
                    "blocked_by_attempt_shell_not_executable",
                    "Attempt shell keeps execution disabled pending future human approval review.",
                    "simulado_attempt_shell",
                    attempt_shell.attempt_shell_id,
                )
            )
        if assembly.no_final_questions_created:
            blockers.append(
                self._blocker(
                    "blocked_by_missing_final_questions",
                    "Final questions are not available for future approval review.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.no_final_answer_keys_created:
            blockers.append(
                self._blocker(
                    "blocked_by_missing_final_answer_keys",
                    "Final answer keys are not available for future approval review.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.no_final_explanations_created:
            blockers.append(
                self._blocker(
                    "blocked_by_missing_final_explanations",
                    "Final explanations are not available for future approval review.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.requires_human_review or attempt_shell.requires_human_finalization:
            blockers.append(
                self._blocker(
                    "blocked_by_human_review_required",
                    "Human review and approval remain required before any future enablement stage.",
                    "simulado_attempt_shell",
                    attempt_shell.attempt_shell_id,
                )
            )
        if assembly.total_candidates == 0 or attempt_shell.review_ready_candidates == 0:
            blockers.append(
                self._blocker(
                    "blocked_by_insufficient_candidates",
                    "There are not enough review-ready candidates to consider future approval review.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if any(
            item.readiness_state == "candidate_blocked_by_unsupported_format"
            for item in assembly.candidates
        ):
            blockers.append(
                self._blocker(
                    "blocked_by_unsupported_format",
                    "At least one candidate remains blocked by unsupported format.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        return blockers

    def _build_findings(
        self,
        assembly: SimuladoQuestionAssembly,
        attempt_shell: SimuladoAttemptShell,
    ) -> list[FinalizationValidationFinding]:
        related_artifact_id = attempt_shell.attempt_shell_id
        return [
            self._finding(
                "approval_required",
                "Human approval remains required before any future finalization stage.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
            self._finding(
                "human_review_required",
                "Human review remains required before any future approval review.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
            self._finding(
                "execution_disabled",
                "Execution remains disabled for this finalization guardrail.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
            self._finding(
                "correction_disabled",
                "Correction remains disabled for this finalization guardrail.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
            self._finding(
                "scoring_disabled",
                "Scoring remains disabled for this finalization guardrail.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
            self._finding(
                "student_submission_disabled",
                "Student submission remains disabled for this finalization guardrail.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
            self._finding(
                "progress_mutation_disabled",
                "Progress mutation remains disabled for this finalization guardrail.",
                "simulado_finalization_guardrail",
                related_artifact_id,
            ),
        ]

    def _build_warnings(
        self,
        assembly: SimuladoQuestionAssembly,
        attempt_shell: SimuladoAttemptShell,
    ) -> list[FinalizationWarning]:
        warnings: list[FinalizationWarning] = []
        if attempt_shell.review_ready_candidates > 0:
            warnings.append(
                self._warning(
                    "candidate_ready_not_finalizable",
                    "Candidate-ready artifacts remain non-finalizable until future human approval exists.",
                    "warning",
                    "simulado_attempt_shell",
                    attempt_shell.attempt_shell_id,
                )
            )
        warnings.append(
            self._warning(
                "attempt_shell_readiness_not_executable",
                "Attempt shell readiness does not enable execution in this pass.",
                "warning",
                "simulado_attempt_shell",
                attempt_shell.attempt_shell_id,
            )
        )
        if assembly.requires_human_review or attempt_shell.requires_human_finalization:
            warnings.append(
                self._warning(
                    "human_approval_review_required",
                    "Future approval review still depends on human review and explicit finalization artifacts.",
                    "warning",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        return warnings

    def _blocker(
        self,
        code: str,
        message: str,
        related_artifact_type: str,
        related_artifact_id: str,
    ) -> FinalizationBlocker:
        return FinalizationBlocker(
            blocker_id=f"finalization-blocker:{code}:{related_artifact_id}",
            code=code,
            severity="blocked",
            message=message,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _finding(
        self,
        code: str,
        message: str,
        related_artifact_type: str,
        related_artifact_id: str,
    ) -> FinalizationValidationFinding:
        return FinalizationValidationFinding(
            finding_id=f"finalization-finding:{code}:{related_artifact_id}",
            code=code,
            severity="info",
            message=message,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        severity: str,
        related_artifact_type: str,
        related_artifact_id: str,
    ) -> FinalizationWarning:
        return FinalizationWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )
