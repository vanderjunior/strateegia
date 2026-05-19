from __future__ import annotations

from app.domain.models import (
    SimuladoAttemptShell,
    SimuladoAttemptShellValidationFinding,
    SimuladoAttemptShellWarning,
    SimuladoExecutionBlocker,
    SimuladoQuestionAssembly,
)
from app.repositories.json_store import JsonStudyRepository


ATTEMPT_SHELL_BUILD_METHOD = "heuristic_simulado_attempt_shell_builder"


class SimuladoAttemptShellService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_attempt_shell(
        self,
        source_assembly_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAttemptShell | None:
        if user_id is None:
            return None
        existing = self.repository.get_simulado_attempt_shell(source_assembly_id, user_id=user_id)
        if existing is not None:
            return existing

        assembly = self.repository.get_simulado_question_assembly_by_id(source_assembly_id, user_id=user_id)
        if assembly is None:
            return None

        blockers = self._build_blockers(assembly)
        warnings = self._build_warnings(assembly)
        validation_findings = self._build_findings(assembly)
        status, readiness_state = self._shell_state(assembly, blockers)

        result = SimuladoAttemptShell(
            attempt_shell_id=f"simulado-attempt-shell:{source_assembly_id}",
            user_id=user_id,
            source_assembly_id=source_assembly_id,
            source_simulado_blueprint_id=assembly.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_candidates=assembly.total_candidates,
            review_ready_candidates=assembly.ready_for_review_count,
            blocked_candidates=assembly.blocked_count,
            needs_review_candidates=assembly.needs_review_count,
            executable_questions_count=0,
            execution_enabled=False,
            correction_enabled=False,
            scoring_enabled=False,
            student_submission_enabled=False,
            progress_mutation_enabled=False,
            requires_human_finalization=True,
            no_student_attempt_created=True,
            no_answer_submission_enabled=True,
            no_correction_result_created=True,
            no_score_created=True,
            validation_findings=validation_findings,
            blockers=blockers,
            warnings=warnings,
            metadata={
                "build_method": ATTEMPT_SHELL_BUILD_METHOD,
                "assembly_status": assembly.status,
                "assembly_readiness_state": assembly.readiness_state,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_attempt_shell(result, user_id=user_id)
        return result

    def get_attempt_shell(
        self,
        source_assembly_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAttemptShell | None:
        return self.repository.get_simulado_attempt_shell(source_assembly_id, user_id=user_id)

    def get_attempt_shell_by_id(
        self,
        attempt_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAttemptShell | None:
        return self.repository.get_simulado_attempt_shell_by_id(attempt_shell_id, user_id=user_id)

    def _shell_state(
        self,
        assembly: SimuladoQuestionAssembly,
        blockers: list[SimuladoExecutionBlocker],
    ) -> tuple[str, str]:
        blocker_codes = {item.code for item in blockers}
        if assembly.total_candidates == 0 or assembly.ready_for_review_count == 0:
            return "execution_readiness_blocked", "blocked_by_insufficient_question_count"
        if "blocked_by_unsupported_format" in blocker_codes:
            return "execution_readiness_blocked", "blocked_by_unsupported_format"
        if assembly.requires_human_review:
            return "execution_readiness_needs_review", "needs_human_finalization"
        if assembly.not_executable:
            return "execution_not_enabled", "blocked_by_non_final_assembly"
        return "execution_readiness_ready_for_future_finalization", "ready_for_future_execution_review"

    def _build_blockers(self, assembly: SimuladoQuestionAssembly) -> list[SimuladoExecutionBlocker]:
        blockers: list[SimuladoExecutionBlocker] = []
        if assembly.not_executable:
            blockers.append(
                self._blocker(
                    "blocked_by_non_final_assembly",
                    "Simulado question assembly remains non-executable in this pass.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.requires_human_review:
            blockers.append(
                self._blocker(
                    "blocked_by_review_required",
                    "Human review and finalization are still required before any future execution stage.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.no_final_questions_created:
            blockers.append(
                self._blocker(
                    "blocked_by_unfinalized_questions",
                    "Final questions are not available for execution.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.no_final_answer_keys_created:
            blockers.append(
                self._blocker(
                    "blocked_by_missing_final_answer_keys",
                    "Final answer keys are not available for execution or correction.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.no_final_explanations_created:
            blockers.append(
                self._blocker(
                    "blocked_by_missing_final_explanations",
                    "Final explanations are not available for execution or review handoff.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.total_candidates == 0 or assembly.ready_for_review_count == 0:
            blockers.append(
                self._blocker(
                    "blocked_by_insufficient_question_count",
                    "There are not enough review-ready candidates to support future execution review.",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if any(item.readiness_state == "candidate_blocked_by_unsupported_format" for item in assembly.candidates):
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
    ) -> list[SimuladoAttemptShellValidationFinding]:
        return [
            self._finding(
                "execution_disabled",
                "Execution remains disabled for this attempt shell.",
                "simulado_attempt_shell",
                assembly.assembly_id,
            ),
            self._finding(
                "correction_disabled",
                "Correction remains disabled for this attempt shell.",
                "simulado_attempt_shell",
                assembly.assembly_id,
            ),
            self._finding(
                "scoring_disabled",
                "Scoring remains disabled for this attempt shell.",
                "simulado_attempt_shell",
                assembly.assembly_id,
            ),
            self._finding(
                "student_submission_disabled",
                "Student answer submission remains disabled for this attempt shell.",
                "simulado_attempt_shell",
                assembly.assembly_id,
            ),
            self._finding(
                "progress_mutation_disabled",
                "Progress mutation remains disabled for this attempt shell.",
                "simulado_attempt_shell",
                assembly.assembly_id,
            ),
            self._finding(
                "no_student_attempt_created",
                "No real student attempt is created in this pass.",
                "simulado_attempt_shell",
                assembly.assembly_id,
            ),
        ]

    def _build_warnings(
        self,
        assembly: SimuladoQuestionAssembly,
    ) -> list[SimuladoAttemptShellWarning]:
        warnings: list[SimuladoAttemptShellWarning] = []
        if assembly.ready_for_review_count > 0:
            warnings.append(
                self._warning(
                    "review_ready_candidates_not_executable",
                    "Review-ready candidates remain non-executable until future human finalization exists.",
                    "warning",
                    "simulado_question_assembly",
                    assembly.assembly_id,
                )
            )
        if assembly.requires_human_review:
            warnings.append(
                self._warning(
                    "human_finalization_required",
                    "Candidate-ready artifacts still require human finalization before any future execution review.",
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
    ) -> SimuladoExecutionBlocker:
        return SimuladoExecutionBlocker(
            blocker_id=f"attempt-shell-blocker:{code}:{related_artifact_id}",
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
    ) -> SimuladoAttemptShellValidationFinding:
        return SimuladoAttemptShellValidationFinding(
            finding_id=f"attempt-shell-finding:{code}:{related_artifact_id}",
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
    ) -> SimuladoAttemptShellWarning:
        return SimuladoAttemptShellWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )
