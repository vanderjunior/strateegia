from __future__ import annotations

from app.domain.models import (
    FinalPedagogicalUpdateEventAuditEntry,
    FinalPedagogicalUpdateEventBlocker,
    FinalPedagogicalUpdateEventSummary,
    FinalPedagogicalUpdateEventValidationFinding,
    FinalPedagogicalUpdateEventWarning,
    ProposedAdaptiveTuningUpdateEntry,
    ProposedCurriculumGraphUpdateEntry,
    ProposedProgressUpdateEntry,
    ProposedRankingUpdateEntry,
    ProposedRetentionUpdateEntry,
    ProposedSchedulerUpdateEntry,
    ProposedStudyCycleUpdateEntry,
    SimuladoControlledRuntimeCommitExecution,
    SimuladoFinalPedagogicalUpdateEvent,
)
from app.repositories.json_store import JsonStudyRepository


FINAL_PEDAGOGICAL_UPDATE_EVENT_BUILD_METHOD = (
    "heuristic_simulado_final_pedagogical_update_event_builder"
)
DRY_RUN_MODES = {"controlled_execution_dry_run", "execution_preview_only"}
SURFACE_PROPOSAL_KIND = {
    "ranking": "ranking_signal_proposal",
    "retention": "retention_signal_proposal",
    "scheduler": "scheduler_signal_proposal",
    "study_cycle": "study_cycle_signal_proposal",
    "curriculum_graph": "curriculum_graph_signal_proposal",
    "adaptive_tuning": "adaptive_tuning_signal_proposal",
}


class SimuladoFinalPedagogicalUpdateEventService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_final_event(
        self,
        source_controlled_execution_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalPedagogicalUpdateEvent | None:
        if user_id is None:
            return None

        controlled_execution = self.repository.get_simulado_controlled_runtime_commit_execution_by_id(
            source_controlled_execution_id,
            user_id=user_id,
        )
        if controlled_execution is None:
            return None

        existing = self.repository.get_simulado_final_pedagogical_update_event(
            source_controlled_execution_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        proposed_progress_updates = self._proposed_progress_updates(controlled_execution)
        proposed_ranking_updates = self._proposed_surface_updates(
            controlled_execution,
            surface_type="ranking",
        )
        proposed_retention_updates = self._proposed_surface_updates(
            controlled_execution,
            surface_type="retention",
        )
        proposed_scheduler_updates = self._proposed_surface_updates(
            controlled_execution,
            surface_type="scheduler",
        )
        proposed_study_cycle_updates = self._proposed_surface_updates(
            controlled_execution,
            surface_type="study_cycle",
        )
        proposed_curriculum_graph_updates = self._proposed_surface_updates(
            controlled_execution,
            surface_type="curriculum_graph",
        )
        proposed_adaptive_tuning_updates = self._proposed_surface_updates(
            controlled_execution,
            surface_type="adaptive_tuning",
        )
        blocker_codes = self._blocker_codes(controlled_execution)
        final_event_status, readiness_state = self._state(blocker_codes)

        result = SimuladoFinalPedagogicalUpdateEvent(
            final_event_id=(
                f"simulado-final-pedagogical-event:{controlled_execution.controlled_execution_id}"
            ),
            user_id=user_id,
            source_controlled_execution_id=controlled_execution.controlled_execution_id,
            source_execution_plan_id=controlled_execution.source_execution_plan_id,
            source_execution_approval_id=controlled_execution.source_execution_approval_id,
            source_execution_guardrail_id=controlled_execution.source_execution_guardrail_id,
            source_commit_transaction_id=controlled_execution.source_commit_transaction_id,
            source_explicit_commit_id=controlled_execution.source_explicit_commit_id,
            source_commit_shell_id=controlled_execution.source_commit_shell_id,
            source_mutation_transaction_id=controlled_execution.source_mutation_transaction_id,
            source_explicit_apply_id=controlled_execution.source_explicit_apply_id,
            source_apply_shell_id=controlled_execution.source_apply_shell_id,
            source_application_id=controlled_execution.source_application_id,
            source_runtime_guardrail_id=controlled_execution.source_runtime_guardrail_id,
            source_integrated_result_id=controlled_execution.source_integrated_result_id,
            source_score_result_id=controlled_execution.source_score_result_id,
            source_progress_guardrail_id=controlled_execution.source_progress_guardrail_id,
            source_attempt_session_id=controlled_execution.source_attempt_session_id,
            source_simulado_blueprint_id=controlled_execution.source_simulado_blueprint_id,
            final_event_mode="event_proposal_only",
            final_event_status=final_event_status,
            readiness_state=readiness_state,
            event_summary=self._summary(
                controlled_execution=controlled_execution,
                proposed_progress_updates=proposed_progress_updates,
                proposed_ranking_updates=proposed_ranking_updates,
                proposed_retention_updates=proposed_retention_updates,
                proposed_scheduler_updates=proposed_scheduler_updates,
                proposed_study_cycle_updates=proposed_study_cycle_updates,
                proposed_curriculum_graph_updates=proposed_curriculum_graph_updates,
                proposed_adaptive_tuning_updates=proposed_adaptive_tuning_updates,
            ),
            proposed_progress_updates=proposed_progress_updates,
            proposed_ranking_updates=proposed_ranking_updates,
            proposed_retention_updates=proposed_retention_updates,
            proposed_scheduler_updates=proposed_scheduler_updates,
            proposed_study_cycle_updates=proposed_study_cycle_updates,
            proposed_curriculum_graph_updates=proposed_curriculum_graph_updates,
            proposed_adaptive_tuning_updates=proposed_adaptive_tuning_updates,
            audit_trail=self._audit_trail(controlled_execution),
            blockers=self._blockers(controlled_execution, blocker_codes),
            validation_findings=self._findings(controlled_execution, blocker_codes),
            warnings=self._warnings(controlled_execution, blocker_codes),
            final_pedagogical_update_event_created=True,
            final_pedagogical_update_event_applied=False,
            final_pedagogical_update_event_apply_allowed=False,
            final_pedagogical_update_event_application_started=False,
            final_pedagogical_update_event_application_completed=False,
            controlled_execution_dry_run_only=True,
            execution_started=False,
            commit_executed=False,
            mutation_committed=False,
            runtime_application_enabled=False,
            runtime_application_applied=False,
            progress_mutation_enabled=False,
            progress_mutation_applied=False,
            ranking_update_enabled=False,
            ranking_update_applied=False,
            retention_update_enabled=False,
            retention_update_applied=False,
            scheduler_update_enabled=False,
            scheduler_update_applied=False,
            study_cycle_update_enabled=False,
            study_cycle_update_applied=False,
            curriculum_graph_update_enabled=False,
            curriculum_graph_update_applied=False,
            adaptive_tuning_enabled=False,
            adaptive_tuning_applied=False,
            no_commit_execution=True,
            no_commit_execution_event_created=True,
            no_mutation_commit=True,
            no_mutation_commit_event_created=True,
            no_runtime_application=True,
            no_progress_mutation=True,
            no_ranking_update=True,
            no_retention_update=True,
            no_scheduler_update=True,
            no_study_cycle_update=True,
            no_curriculum_graph_update=True,
            no_adaptive_tuning_update=True,
            no_applied_final_pedagogical_update_event=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": FINAL_PEDAGOGICAL_UPDATE_EVENT_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_final_pedagogical_update_event(
            result,
            user_id=user_id,
        )
        return result

    def get_final_event(
        self,
        source_controlled_execution_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalPedagogicalUpdateEvent | None:
        return self.repository.get_simulado_final_pedagogical_update_event(
            source_controlled_execution_id,
            user_id=user_id,
        )

    def get_final_event_by_id(
        self,
        final_event_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalPedagogicalUpdateEvent | None:
        return self.repository.get_simulado_final_pedagogical_update_event_by_id(
            final_event_id,
            user_id=user_id,
        )

    def _summary(
        self,
        *,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
        proposed_progress_updates: list[ProposedProgressUpdateEntry],
        proposed_ranking_updates: list[ProposedRankingUpdateEntry],
        proposed_retention_updates: list[ProposedRetentionUpdateEntry],
        proposed_scheduler_updates: list[ProposedSchedulerUpdateEntry],
        proposed_study_cycle_updates: list[ProposedStudyCycleUpdateEntry],
        proposed_curriculum_graph_updates: list[ProposedCurriculumGraphUpdateEntry],
        proposed_adaptive_tuning_updates: list[ProposedAdaptiveTuningUpdateEntry],
    ) -> FinalPedagogicalUpdateEventSummary:
        return FinalPedagogicalUpdateEventSummary(
            summary_id=(
                f"final-pedagogical-update-event-summary:{controlled_execution.controlled_execution_id}"
            ),
            source_controlled_execution_present=True,
            source_controlled_execution_dry_run=(
                controlled_execution.execution_mode in DRY_RUN_MODES
            ),
            source_execution_started=controlled_execution.execution_started,
            source_commit_executed=controlled_execution.commit_executed,
            source_mutation_committed=controlled_execution.mutation_committed,
            source_runtime_application_performed=controlled_execution.runtime_application_applied,
            source_real_execution_performed=(
                controlled_execution.execution_started
                or controlled_execution.commit_executed
                or controlled_execution.mutation_committed
            ),
            proposed_progress_update_count=len(proposed_progress_updates),
            proposed_ranking_update_count=len(proposed_ranking_updates),
            proposed_retention_update_count=len(proposed_retention_updates),
            proposed_scheduler_update_count=len(proposed_scheduler_updates),
            proposed_study_cycle_update_count=len(proposed_study_cycle_updates),
            proposed_curriculum_graph_update_count=len(proposed_curriculum_graph_updates),
            proposed_adaptive_tuning_update_count=len(proposed_adaptive_tuning_updates),
            final_event_apply_allowed=False,
            final_event_applied=False,
            unsafe_public_answer_key_exposure_detected=(
                controlled_execution.answer_key_publicly_exposed
                or controlled_execution.gabarito_publicly_exposed
            ),
            unsafe_gabarito_exposure_detected=controlled_execution.gabarito_publicly_exposed,
            metadata={},
        )

    def _proposed_progress_updates(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
    ) -> list[ProposedProgressUpdateEntry]:
        entries: list[ProposedProgressUpdateEntry] = []
        for item in controlled_execution.progress_step_execution_records:
            entries.append(
                ProposedProgressUpdateEntry(
                    entry_id=f"proposed-progress-update:{item.record_id}",
                    update_kind="progress_delta_proposal",
                    source_record_id=item.record_id,
                    target_type=item.target_type,
                    target_id=item.source_progress_approval_id,
                    proposed=True,
                    applied=False,
                    apply_allowed=False,
                    bounded_summary={
                        "target_type": item.target_type,
                        "delta_kind": item.delta_kind,
                        "execution_record_status": item.execution_record_status,
                        "blocked": item.blocked,
                    },
                    blockers=list(item.blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return entries

    def _proposed_surface_updates(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
        *,
        surface_type: str,
    ) -> list[
        ProposedRankingUpdateEntry
        | ProposedRetentionUpdateEntry
        | ProposedSchedulerUpdateEntry
        | ProposedStudyCycleUpdateEntry
        | ProposedCurriculumGraphUpdateEntry
        | ProposedAdaptiveTuningUpdateEntry
    ]:
        entry_cls = {
            "ranking": ProposedRankingUpdateEntry,
            "retention": ProposedRetentionUpdateEntry,
            "scheduler": ProposedSchedulerUpdateEntry,
            "study_cycle": ProposedStudyCycleUpdateEntry,
            "curriculum_graph": ProposedCurriculumGraphUpdateEntry,
            "adaptive_tuning": ProposedAdaptiveTuningUpdateEntry,
        }[surface_type]
        entries = []
        for item in controlled_execution.surface_step_execution_records:
            if item.surface_type != surface_type:
                continue
            entries.append(
                entry_cls(
                    entry_id=f"proposed-{surface_type}-update:{item.record_id}",
                    update_kind=SURFACE_PROPOSAL_KIND.get(surface_type, "unknown"),
                    source_record_id=item.record_id,
                    target_type=item.surface_type,
                    target_id=item.source_surface_approval_id,
                    proposed=True,
                    applied=False,
                    apply_allowed=False,
                    bounded_summary={
                        "surface_type": item.surface_type,
                        "update_kind": item.update_kind,
                        "execution_record_status": item.execution_record_status,
                        "blocked": item.blocked,
                    },
                    blockers=list(item.blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return entries

    def _audit_trail(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
    ) -> list[FinalPedagogicalUpdateEventAuditEntry]:
        return [
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:created"
                ),
                event_type="final_pedagogical_update_event_created",
                actor_user_id=controlled_execution.user_id,
                message="Final pedagogical update event proposal artifact created.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:proposal"
                ),
                event_type="final_event_proposal_created",
                actor_user_id=controlled_execution.user_id,
                message="Final pedagogical update event remains a dry-run proposal only.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:blocked"
                ),
                event_type="final_event_blocked",
                actor_user_id=controlled_execution.user_id,
                message="Final pedagogical update event application remains blocked.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:not-applied"
                ),
                event_type="final_event_not_applied",
                actor_user_id=controlled_execution.user_id,
                message="Final pedagogical update event was not applied.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-commit"
                ),
                event_type="no_commit_execution",
                actor_user_id=controlled_execution.user_id,
                message="No commit execution was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-mutation"
                ),
                event_type="no_mutation_commit",
                actor_user_id=controlled_execution.user_id,
                message="No mutation commit was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-runtime"
                ),
                event_type="no_runtime_application",
                actor_user_id=controlled_execution.user_id,
                message="No runtime application was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-progress"
                ),
                event_type="no_progress_mutation",
                actor_user_id=controlled_execution.user_id,
                message="No progress mutation was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-ranking"
                ),
                event_type="no_ranking_update",
                actor_user_id=controlled_execution.user_id,
                message="No ranking update was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-retention"
                ),
                event_type="no_retention_update",
                actor_user_id=controlled_execution.user_id,
                message="No retention update was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-scheduler"
                ),
                event_type="no_scheduler_update",
                actor_user_id=controlled_execution.user_id,
                message="No scheduler update was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-study-cycle"
                ),
                event_type="no_study_cycle_update",
                actor_user_id=controlled_execution.user_id,
                message="No study cycle update was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-graph"
                ),
                event_type="no_curriculum_graph_update",
                actor_user_id=controlled_execution.user_id,
                message="No curriculum graph update was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-tuning"
                ),
                event_type="no_adaptive_tuning_update",
                actor_user_id=controlled_execution.user_id,
                message="No adaptive tuning update was performed.",
                metadata={},
            ),
            FinalPedagogicalUpdateEventAuditEntry(
                audit_id=(
                    f"final-pedagogical-update-event-audit:{controlled_execution.controlled_execution_id}:no-applied"
                ),
                event_type="no_applied_final_pedagogical_update_event",
                actor_user_id=controlled_execution.user_id,
                message="No applied final pedagogical update event was created.",
                metadata={},
            ),
        ]

    def _blocker_codes(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
    ) -> list[str]:
        if controlled_execution.answer_key_publicly_exposed or controlled_execution.gabarito_publicly_exposed:
            return ["blocked_by_public_answer_key_exposure_forbidden"]
        if controlled_execution.execution_mode not in DRY_RUN_MODES:
            return ["blocked_by_controlled_execution_not_dry_run"]
        if controlled_execution.execution_started:
            return ["blocked_by_controlled_execution_started"]
        if controlled_execution.commit_executed:
            return ["blocked_by_commit_executed"]
        if controlled_execution.mutation_committed:
            return ["blocked_by_mutation_committed"]
        if controlled_execution.runtime_application_applied:
            return ["blocked_by_runtime_application_detected"]
        if controlled_execution.progress_mutation_applied:
            return ["blocked_by_progress_mutation_detected"]
        if bool(controlled_execution.metadata.get("final_event_apply_disabled")) or (
            controlled_execution.readiness_state == "blocked_by_execution_disabled"
        ) or any(
            blocker.code == "blocked_by_execution_disabled"
            for blocker in controlled_execution.blockers
        ):
            return ["blocked_by_final_event_apply_disabled"]
        return ["blocked_by_final_event_apply_disabled"]

    def _state(self, blocker_codes: list[str]) -> tuple[str, str]:
        if blocker_codes:
            return ("final_event_blocked", blocker_codes[0])
        return ("final_event_proposed_not_applied", "final_event_ready_for_future_apply_policy_review")

    def _blockers(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
        blocker_codes: list[str],
    ) -> list[FinalPedagogicalUpdateEventBlocker]:
        messages = {
            "blocked_by_controlled_execution_not_dry_run": "Source controlled execution is not bounded to dry-run mode.",
            "blocked_by_controlled_execution_started": "Source controlled execution has already started.",
            "blocked_by_commit_executed": "Source controlled execution indicates commit execution.",
            "blocked_by_mutation_committed": "Source controlled execution indicates mutation commit.",
            "blocked_by_runtime_application_detected": "Source controlled execution indicates runtime application.",
            "blocked_by_progress_mutation_detected": "Source controlled execution indicates progress mutation.",
            "blocked_by_final_event_apply_disabled": "Final pedagogical update event application remains disabled.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key exposure prevents final event proposal readiness.",
        }
        return [
            FinalPedagogicalUpdateEventBlocker(
                blocker_id=f"final-pedagogical-update-event-blocker:{controlled_execution.controlled_execution_id}:{code}",
                code=code,
                message=messages.get(code, code.replace("_", " ")),
                related_artifact_type="simulado_controlled_runtime_commit_execution",
                related_artifact_id=controlled_execution.controlled_execution_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
        blocker_codes: list[str],
    ) -> list[FinalPedagogicalUpdateEventValidationFinding]:
        return [
            FinalPedagogicalUpdateEventValidationFinding(
                finding_id=(
                    f"final-pedagogical-update-event-finding:{controlled_execution.controlled_execution_id}:proposal"
                ),
                code=(
                    "final_event_proposal_blocked"
                    if blocker_codes
                    else "final_event_proposal_ready_for_review"
                ),
                message="Final pedagogical update event remains a proposal-only artifact.",
                related_artifact_type="simulado_controlled_runtime_commit_execution",
                related_artifact_id=controlled_execution.controlled_execution_id,
                metadata={"blocker_count": len(blocker_codes)},
            )
        ]

    def _warnings(
        self,
        controlled_execution: SimuladoControlledRuntimeCommitExecution,
        blocker_codes: list[str],
    ) -> list[FinalPedagogicalUpdateEventWarning]:
        warnings = [
            FinalPedagogicalUpdateEventWarning(
                code="final_event_proposal_only",
                message="This final pedagogical update event is a dry-run proposal only.",
                related_artifact_type="simulado_controlled_runtime_commit_execution",
                related_artifact_id=controlled_execution.controlled_execution_id,
                metadata={},
            )
        ]
        if blocker_codes:
            warnings.append(
                FinalPedagogicalUpdateEventWarning(
                    code="final_event_contains_blockers",
                    message="Final pedagogical update event proposal remains blocked by policy or source state.",
                    related_artifact_type="simulado_controlled_runtime_commit_execution",
                    related_artifact_id=controlled_execution.controlled_execution_id,
                    metadata={"blocker_count": len(blocker_codes)},
                )
            )
        return warnings
