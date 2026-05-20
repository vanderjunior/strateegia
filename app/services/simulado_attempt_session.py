from __future__ import annotations

from app.domain.models import (
    AttemptSessionBlocker,
    AttemptSessionTimingPlan,
    AttemptSessionValidationFinding,
    AttemptSessionWarning,
    ExecutionShellCandidateRecord,
    SimuladoAttemptSession,
    SimuladoAttemptSessionItem,
    SimuladoExecutionShell,
)
from app.repositories.json_store import JsonStudyRepository


ATTEMPT_SESSION_BUILD_METHOD = "heuristic_simulado_attempt_session_builder"
MESSAGE_MAX_LENGTH = 240


class SimuladoAttemptSessionService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_attempt_session(
        self,
        source_execution_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAttemptSession | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_attempt_session(
            source_execution_shell_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        execution_shell = self.repository.get_simulado_execution_shell_by_id(
            source_execution_shell_id,
            user_id=user_id,
        )
        if execution_shell is None:
            return None

        items = self._items(execution_shell)
        blockers = self._blockers(execution_shell, items)
        validation_findings = self._findings(execution_shell)
        warnings = self._warnings(execution_shell)
        status, readiness_state = self._session_state(execution_shell)
        blocked_item_count = sum(1 for item in items if item.can_be_displayed is False)

        result = SimuladoAttemptSession(
            attempt_session_id=f"simulado-attempt-session:{source_execution_shell_id}",
            user_id=user_id,
            source_execution_shell_id=source_execution_shell_id,
            source_final_approval_artifact_id=execution_shell.source_final_approval_artifact_id,
            source_simulado_blueprint_id=execution_shell.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_items=len(items),
            prepared_item_count=len(items),
            blocked_item_count=blocked_item_count,
            items=items,
            timing_plan=self._timing_plan(execution_shell),
            blockers=blockers,
            validation_findings=validation_findings,
            warnings=warnings,
            session_prepared=True,
            session_active=False,
            session_submitted=False,
            session_completed=False,
            answer_submission_enabled=False,
            correction_enabled=False,
            scoring_enabled=False,
            progress_mutation_enabled=False,
            no_answer_submission_created=True,
            no_correction_result_created=True,
            no_score_created=True,
            no_progress_mutation=True,
            metadata={
                "build_method": ATTEMPT_SESSION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_attempt_session(result, user_id=user_id)
        return result

    def get_attempt_session(
        self,
        source_execution_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAttemptSession | None:
        return self.repository.get_simulado_attempt_session(
            source_execution_shell_id,
            user_id=user_id,
        )

    def get_attempt_session_by_id(
        self,
        attempt_session_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAttemptSession | None:
        return self.repository.get_simulado_attempt_session_by_id(
            attempt_session_id,
            user_id=user_id,
        )

    def _items(self, execution_shell: SimuladoExecutionShell) -> list[SimuladoAttemptSessionItem]:
        ordered = sorted(
            execution_shell.candidate_records,
            key=lambda item: (item.order_index, item.display_position, str(item.source_candidate_id or "")),
        )
        items: list[SimuladoAttemptSessionItem] = []
        for record in ordered:
            item_readiness_state = self._item_readiness_state(record)
            items.append(
                SimuladoAttemptSessionItem(
                    item_id=f"attempt-session-item:{record.record_id}",
                    source_execution_candidate_record_id=record.record_id,
                    source_candidate_id=record.source_candidate_id,
                    order_index=record.order_index,
                    display_position=record.display_position,
                    item_status="item_blocked" if record.can_be_presented_to_student is False else "item_prepared",
                    item_readiness_state=item_readiness_state,
                    can_be_displayed=False,
                    can_accept_answer=False,
                    has_submitted_answer=False,
                    can_be_corrected=False,
                    can_be_scored=False,
                    blockers=self._item_blockers(record, item_readiness_state),
                    warnings=list(record.warnings),
                    metadata={"approval_state": record.approval_state},
                )
            )
        return items

    def _item_readiness_state(self, record: ExecutionShellCandidateRecord) -> str:
        if not record.has_final_question or not record.has_final_answer_key or not record.has_final_explanation:
            return "item_blocked_by_missing_final_content"
        if record.execution_readiness_state == "candidate_execution_needs_review":
            return "item_needs_review"
        if record.execution_readiness_state == "candidate_ready_for_future_activation_review":
            return "item_prepared_non_submittable"
        return "item_blocked_by_non_executable_candidate"

    def _item_blockers(
        self,
        record: ExecutionShellCandidateRecord,
        item_readiness_state: str,
    ) -> list[str]:
        blockers = list(record.blockers)
        if item_readiness_state == "item_blocked_by_missing_final_content":
            blockers.append("blocked_by_missing_final_content")
        elif item_readiness_state == "item_blocked_by_non_executable_candidate":
            blockers.append("blocked_by_no_executable_items")
        return sorted(set(blockers))

    def _session_state(self, execution_shell: SimuladoExecutionShell) -> tuple[str, str]:
        if execution_shell.executable_candidate_count == 0:
            return "attempt_session_blocked", "blocked_by_no_executable_items"
        return "attempt_session_prepared", "prepared_non_submittable"

    def _timing_plan(self, execution_shell: SimuladoExecutionShell) -> AttemptSessionTimingPlan:
        return AttemptSessionTimingPlan(
            timing_plan_id=f"attempt-session-timing:{execution_shell.execution_shell_id}",
            timing_available=False,
            estimated_duration_minutes=execution_shell.operational_summary.estimated_duration_minutes,
            per_item_time_limit_seconds=None,
            timer_active=False,
            timer_started_at=None,
            timer_completed_at=None,
            metadata={},
        )

    def _blockers(
        self,
        execution_shell: SimuladoExecutionShell,
        items: list[SimuladoAttemptSessionItem],
    ) -> list[AttemptSessionBlocker]:
        related_id = execution_shell.execution_shell_id
        blockers = [
            self._blocker(
                "blocked_by_execution_shell_inactive",
                "Execution shell remains inactive for this prepared attempt session.",
                related_id,
            ),
            self._blocker(
                "blocked_by_submission_disabled",
                "Answer submission remains disabled for this prepared attempt session.",
                related_id,
            ),
            self._blocker(
                "blocked_by_correction_disabled",
                "Correction remains disabled for this prepared attempt session.",
                related_id,
            ),
            self._blocker(
                "blocked_by_scoring_disabled",
                "Scoring remains disabled for this prepared attempt session.",
                related_id,
            ),
        ]
        if execution_shell.executable_candidate_count == 0:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_no_executable_items",
                    "No executable items are available for this prepared attempt session.",
                    related_id,
                ),
            )
        if any(item.item_readiness_state == "item_blocked_by_missing_final_content" for item in items):
            blockers.append(
                self._blocker(
                    "blocked_by_missing_final_content",
                    "Final content remains unavailable for this prepared attempt session.",
                    related_id,
                )
            )
        return blockers

    def _findings(self, execution_shell: SimuladoExecutionShell) -> list[AttemptSessionValidationFinding]:
        related_id = execution_shell.execution_shell_id
        return [
            self._finding("session_prepared", "Prepared attempt session artifact created in this pass.", related_id),
            self._finding("session_inactive", "Attempt session remains inactive in this pass.", related_id),
            self._finding("submission_disabled", "Answer submission remains disabled in this pass.", related_id),
            self._finding("correction_disabled", "Correction remains disabled in this pass.", related_id),
            self._finding("scoring_disabled", "Scoring remains disabled in this pass.", related_id),
            self._finding("progress_mutation_disabled", "Progress mutation remains disabled in this pass.", related_id),
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
            self._finding(
                "no_progress_mutation",
                "No study progress mutation is performed in this pass.",
                related_id,
            ),
        ]

    def _warnings(self, execution_shell: SimuladoExecutionShell) -> list[AttemptSessionWarning]:
        return [
            self._warning(
                "prepared_non_submittable_session",
                "Prepared attempt session remains non-submittable until a future submission foundation exists.",
                execution_shell.execution_shell_id,
            )
        ]

    def _blocker(self, code: str, message: str, related_id: str) -> AttemptSessionBlocker:
        return AttemptSessionBlocker(
            blocker_id=f"attempt-session-blocker:{code}:{related_id}",
            code=code,
            severity="blocked",
            message=self._truncate(message, MESSAGE_MAX_LENGTH),
            related_artifact_type="simulado_attempt_session",
            related_artifact_id=related_id,
            metadata={},
        )

    def _finding(self, code: str, message: str, related_id: str) -> AttemptSessionValidationFinding:
        return AttemptSessionValidationFinding(
            finding_id=f"attempt-session-finding:{code}:{related_id}",
            code=code,
            severity="info",
            message=self._truncate(message, MESSAGE_MAX_LENGTH),
            related_artifact_type="simulado_attempt_session",
            related_artifact_id=related_id,
            metadata={},
        )

    def _warning(self, code: str, message: str, related_id: str) -> AttemptSessionWarning:
        return AttemptSessionWarning(
            code=code,
            message=self._truncate(message, MESSAGE_MAX_LENGTH),
            severity="warning",
            related_artifact_type="simulado_attempt_session",
            related_artifact_id=related_id,
            metadata={},
        )

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 3)] + "..."
