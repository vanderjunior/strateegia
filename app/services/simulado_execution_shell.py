from __future__ import annotations

from app.domain.models import (
    ExecutionShellBlocker,
    ExecutionShellCandidateRecord,
    ExecutionShellOperationalSummary,
    ExecutionShellValidationFinding,
    ExecutionShellWarning,
    FinalApprovalCandidateRecord,
    SimuladoExecutionShell,
    SimuladoFinalApprovalArtifact,
)
from app.repositories.json_store import JsonStudyRepository


EXECUTION_SHELL_BUILD_METHOD = "heuristic_simulado_execution_shell_builder"
MESSAGE_MAX_LENGTH = 240


class SimuladoExecutionShellService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_execution_shell(
        self,
        source_final_approval_artifact_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExecutionShell | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_execution_shell(
            source_final_approval_artifact_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        artifact = self.repository.get_simulado_final_approval_artifact_by_id(
            source_final_approval_artifact_id,
            user_id=user_id,
        )
        if artifact is None:
            return None

        candidate_records = self._candidate_records(artifact)
        blockers = self._blockers(artifact)
        validation_findings = self._findings(artifact)
        warnings = self._warnings(artifact)
        status, readiness_state = self._shell_state(artifact)

        result = SimuladoExecutionShell(
            execution_shell_id=f"simulado-execution-shell:{source_final_approval_artifact_id}",
            user_id=user_id,
            source_final_approval_artifact_id=source_final_approval_artifact_id,
            source_finalization_guardrail_id=artifact.source_finalization_guardrail_id,
            source_attempt_shell_id=artifact.source_attempt_shell_id,
            source_assembly_id=artifact.source_assembly_id,
            source_simulado_blueprint_id=artifact.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_candidates=artifact.total_candidates,
            approved_candidate_count=artifact.approved_candidate_count,
            blocked_candidate_count=artifact.blocked_candidate_count + artifact.rejected_candidate_count,
            needs_review_candidate_count=artifact.needs_review_candidate_count + artifact.not_reviewed_candidate_count,
            executable_candidate_count=0,
            candidate_records=candidate_records,
            operational_summary=self._operational_summary(artifact),
            blockers=blockers,
            validation_findings=validation_findings,
            warnings=warnings,
            execution_shell_active=False,
            execution_started=False,
            attempt_created=False,
            student_submission_enabled=False,
            correction_enabled=False,
            scoring_enabled=False,
            progress_mutation_enabled=False,
            no_student_attempt_created=True,
            no_answer_submission_created=True,
            no_correction_result_created=True,
            no_score_created=True,
            metadata={
                "build_method": EXECUTION_SHELL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_execution_shell(result, user_id=user_id)
        return result

    def get_execution_shell(
        self,
        source_final_approval_artifact_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExecutionShell | None:
        return self.repository.get_simulado_execution_shell(
            source_final_approval_artifact_id,
            user_id=user_id,
        )

    def get_execution_shell_by_id(
        self,
        execution_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExecutionShell | None:
        return self.repository.get_simulado_execution_shell_by_id(
            execution_shell_id,
            user_id=user_id,
        )

    def _candidate_records(
        self,
        artifact: SimuladoFinalApprovalArtifact,
    ) -> list[ExecutionShellCandidateRecord]:
        ordered = sorted(
            artifact.candidate_records,
            key=lambda item: (str(item.source_candidate_id or ""), str(item.record_id)),
        )
        records: list[ExecutionShellCandidateRecord] = []
        for order_index, item in enumerate(ordered):
            records.append(
                ExecutionShellCandidateRecord(
                    record_id=f"execution-shell-record:{item.record_id}",
                    source_candidate_id=item.source_candidate_id,
                    source_approval_record_id=item.record_id,
                    approval_state=item.approval_state,
                    execution_readiness_state=self._execution_readiness_state(item),
                    order_index=order_index,
                    display_position=order_index + 1,
                    has_final_question=False,
                    has_final_answer_key=False,
                    has_final_explanation=False,
                    can_be_presented_to_student=False,
                    can_accept_answer=False,
                    can_be_corrected=False,
                    can_be_scored=False,
                    blockers=self._candidate_blockers(item),
                    warnings=list(item.warnings),
                    metadata={
                        "requires_human_review": item.requires_human_review,
                        "decision_id": item.decision_id,
                    },
                )
            )
        return records

    def _execution_readiness_state(self, record: FinalApprovalCandidateRecord) -> str:
        if record.approval_state == "candidate_approved_for_future_execution_review":
            return "candidate_ready_for_future_activation_review"
        if record.approval_state == "candidate_needs_revision":
            return "candidate_execution_needs_review"
        if record.approval_state in {"candidate_blocked", "candidate_rejected"}:
            return "candidate_execution_blocked"
        return "candidate_blocked_by_unapproved_state"

    def _candidate_blockers(self, record: FinalApprovalCandidateRecord) -> list[str]:
        blockers = list(record.blockers)
        if record.approval_state != "candidate_approved_for_future_execution_review":
            blockers.append("candidate_blocked_by_unapproved_state")
        if "candidate_blocked_by_unapproved_state" not in blockers and record.approval_state != "candidate_approved_for_future_execution_review":
            blockers.append("candidate_blocked_by_unapproved_state")
        return sorted(set(blockers))

    def _shell_state(self, artifact: SimuladoFinalApprovalArtifact) -> tuple[str, str]:
        if artifact.approved_candidate_count == 0:
            return "execution_shell_blocked", "blocked_by_no_approved_candidates"
        return "execution_shell_needs_review", "needs_future_activation_review"

    def _operational_summary(
        self,
        artifact: SimuladoFinalApprovalArtifact,
    ) -> ExecutionShellOperationalSummary:
        return ExecutionShellOperationalSummary(
            summary_id=f"execution-shell-summary:{artifact.approval_artifact_id}",
            has_final_approval_artifact=True,
            has_approved_candidates=artifact.approved_candidate_count > 0,
            has_final_questions=False,
            has_final_answer_keys=False,
            has_final_explanations=False,
            has_execution_session=False,
            future_execution_possible_after_finalization=artifact.approved_candidate_count > 0,
            execution_disabled_reason=self._truncate(
                "Execution remains disabled because final questions, answer keys and explanations are still unavailable and operational execution is not enabled in this pass.",
                MESSAGE_MAX_LENGTH,
            ),
            candidate_ordering_strategy="stable_source_candidate_id",
            estimated_question_count=artifact.total_candidates,
            estimated_duration_minutes=max(0, artifact.total_candidates * 2),
            metadata={},
        )

    def _blockers(self, artifact: SimuladoFinalApprovalArtifact) -> list[ExecutionShellBlocker]:
        related_id = artifact.approval_artifact_id
        blockers = [
            self._blocker(
                "blocked_by_missing_final_questions",
                "Final questions remain unavailable for operational execution.",
                related_id,
            ),
            self._blocker(
                "blocked_by_missing_final_answer_keys",
                "Final answer keys remain unavailable for operational execution.",
                related_id,
            ),
            self._blocker(
                "blocked_by_missing_final_explanations",
                "Final explanations remain unavailable for operational execution.",
                related_id,
            ),
            self._blocker(
                "blocked_by_execution_not_enabled",
                "Execution remains disabled for this execution shell.",
                related_id,
            ),
            self._blocker(
                "blocked_by_submission_not_enabled",
                "Student submission remains disabled for this execution shell.",
                related_id,
            ),
            self._blocker(
                "blocked_by_correction_not_enabled",
                "Correction remains disabled for this execution shell.",
                related_id,
            ),
            self._blocker(
                "blocked_by_scoring_not_enabled",
                "Scoring remains disabled for this execution shell.",
                related_id,
            ),
        ]
        if artifact.approved_candidate_count == 0:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_no_approved_candidates",
                    "No candidates were approved for future execution review.",
                    related_id,
                ),
            )
        if artifact.not_reviewed_candidate_count > 0:
            blockers.append(
                self._blocker(
                    "blocked_by_unreviewed_candidates",
                    "Some candidates still require human review before any future activation review.",
                    related_id,
                )
            )
        return blockers

    def _findings(self, artifact: SimuladoFinalApprovalArtifact) -> list[ExecutionShellValidationFinding]:
        related_id = artifact.approval_artifact_id
        return [
            self._finding("execution_shell_inactive", "Execution shell remains non-active in this pass.", related_id),
            self._finding("execution_disabled", "Execution remains disabled in this pass.", related_id),
            self._finding("submission_disabled", "Student submission remains disabled in this pass.", related_id),
            self._finding("correction_disabled", "Correction remains disabled in this pass.", related_id),
            self._finding("scoring_disabled", "Scoring remains disabled in this pass.", related_id),
            self._finding(
                "progress_mutation_disabled",
                "Progress mutation remains disabled in this pass.",
                related_id,
            ),
            self._finding(
                "no_student_attempt_created",
                "No real student attempt is created in this pass.",
                related_id,
            ),
            self._finding(
                "no_answer_submission_created",
                "No answer submission is created in this pass.",
                related_id,
            ),
            self._finding(
                "no_correction_result_created",
                "No correction result is created in this pass.",
                related_id,
            ),
            self._finding("no_score_created", "No score is created in this pass.", related_id),
        ]

    def _warnings(self, artifact: SimuladoFinalApprovalArtifact) -> list[ExecutionShellWarning]:
        warnings: list[ExecutionShellWarning] = []
        if artifact.approved_candidate_count > 0:
            warnings.append(
                self._warning(
                    "approved_candidates_remain_non_executable",
                    "Approved candidates remain non-executable and non-scoreable in this pass.",
                    artifact.approval_artifact_id,
                )
            )
        return warnings

    def _blocker(self, code: str, message: str, related_id: str) -> ExecutionShellBlocker:
        return ExecutionShellBlocker(
            blocker_id=f"execution-shell-blocker:{code}:{related_id}",
            code=code,
            severity="blocked",
            message=self._truncate(message, MESSAGE_MAX_LENGTH),
            related_artifact_type="simulado_execution_shell",
            related_artifact_id=related_id,
            metadata={},
        )

    def _finding(self, code: str, message: str, related_id: str) -> ExecutionShellValidationFinding:
        return ExecutionShellValidationFinding(
            finding_id=f"execution-shell-finding:{code}:{related_id}",
            code=code,
            severity="info",
            message=self._truncate(message, MESSAGE_MAX_LENGTH),
            related_artifact_type="simulado_execution_shell",
            related_artifact_id=related_id,
            metadata={},
        )

    def _warning(self, code: str, message: str, related_id: str) -> ExecutionShellWarning:
        return ExecutionShellWarning(
            code=code,
            message=self._truncate(message, MESSAGE_MAX_LENGTH),
            severity="warning",
            related_artifact_type="simulado_execution_shell",
            related_artifact_id=related_id,
            metadata={},
        )

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 3)] + "..."
