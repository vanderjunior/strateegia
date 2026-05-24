from __future__ import annotations

from app.domain.models import (
    CandidateAdaptiveTuningPropagationTarget,
    CandidateCurriculumGraphPropagationTarget,
    CandidateRankingPropagationTarget,
    CandidateRetentionPropagationTarget,
    CandidateSchedulerPropagationTarget,
    CandidateStudyCyclePropagationTarget,
    ControlledPropagationApplyAuditEntry,
    ControlledPropagationApplyBlocker,
    ControlledPropagationApplySummary,
    ControlledPropagationApplyValidationFinding,
    ControlledPropagationApplyWarning,
    ControlledPropagationEntry,
    ControlledPropagationIdempotencyRecord,
    ControlledPropagationRollbackRecord,
    ControlledPropagationSourceGuardrailSummary,
    SimuladoControlledPropagationApply,
    SimuladoPropagationGuardrail,
)
from app.repositories.json_store import JsonStudyRepository


CONTROLLED_PROPAGATION_APPLY_BUILD_METHOD = (
    "heuristic_simulado_controlled_propagation_apply_builder"
)


class SimuladoControlledPropagationApplyService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_controlled_propagation_apply(
        self,
        source_propagation_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledPropagationApply | None:
        if user_id is None:
            return None

        source_guardrail = self.repository.get_simulado_propagation_guardrail_by_id(
            source_propagation_guardrail_id,
            user_id=user_id,
        )
        if source_guardrail is None:
            return None

        existing = self.repository.get_simulado_controlled_propagation_apply(
            source_propagation_guardrail_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        blocker_code = self._blocker_code(source_guardrail)
        ready = blocker_code == "controlled_propagation_ready"
        controlled_entries = self._controlled_entries(source_guardrail) if ready else []
        idempotency_key = self._idempotency_key(source_guardrail)
        entry_count = len(controlled_entries)
        candidate_count = self._candidate_count(source_guardrail)
        apply_status = (
            "controlled_propagation_ledger_recorded"
            if ready
            else "controlled_propagation_blocked"
        )
        readiness_state = (
            "controlled_propagation_ledger_recorded" if ready else blocker_code
        )

        result = SimuladoControlledPropagationApply(
            controlled_propagation_apply_id=(
                "simulado-controlled-propagation-apply:"
                f"{source_guardrail.propagation_guardrail_id}"
            ),
            user_id=user_id,
            source_propagation_guardrail_id=source_guardrail.propagation_guardrail_id,
            source_applied_event_ledger_id=source_guardrail.source_applied_event_ledger_id,
            source_minimal_progress_ledger_apply_id=(
                source_guardrail.source_minimal_progress_ledger_apply_id
            ),
            source_runtime_apply_policy_id=source_guardrail.source_runtime_apply_policy_id,
            source_final_event_id=source_guardrail.source_final_event_id,
            source_controlled_execution_id=source_guardrail.source_controlled_execution_id,
            source_execution_plan_id=source_guardrail.source_execution_plan_id,
            source_execution_approval_id=source_guardrail.source_execution_approval_id,
            source_score_result_id=source_guardrail.source_score_result_id,
            source_progress_guardrail_id=source_guardrail.source_progress_guardrail_id,
            source_integrated_result_id=source_guardrail.source_integrated_result_id,
            source_attempt_session_id=source_guardrail.source_attempt_session_id,
            source_simulado_blueprint_id=source_guardrail.source_simulado_blueprint_id,
            apply_mode="controlled_propagation_apply",
            apply_status=apply_status,
            readiness_state=readiness_state,
            apply_summary=self._summary(
                source_guardrail=source_guardrail,
                candidate_count=candidate_count,
                entry_count=entry_count,
                ready=ready,
                idempotency_key=idempotency_key,
            ),
            source_guardrail_summary=self._source_guardrail_summary(source_guardrail),
            controlled_propagation_entries=controlled_entries,
            idempotency_record=self._idempotency_record(source_guardrail, idempotency_key),
            rollback_record=self._rollback_record(source_guardrail, ready),
            audit_trail=self._audit_trail(source_guardrail, ready, entry_count),
            blockers=self._blockers(source_guardrail, blocker_code, ready),
            validation_findings=self._validation_findings(
                source_guardrail,
                blocker_code,
                ready,
            ),
            warnings=self._warnings(source_guardrail, ready),
            controlled_propagation_apply_created=True,
            controlled_propagation_allowed=ready,
            controlled_propagation_applied=ready,
            controlled_propagation_ledger_recorded=bool(controlled_entries),
            controlled_propagation_entry_created=bool(controlled_entries),
            controlled_propagation_entry_count=entry_count,
            source_guardrail_present=True,
            source_guardrail_ready_for_future_review=(
                source_guardrail.propagation_ready_for_future_review
            ),
            source_propagation_allowed_now=source_guardrail.propagation_allowed_now,
            source_propagation_applied=source_guardrail.propagation_applied,
            source_candidate_target_count=candidate_count,
            idempotency_key_required=True,
            idempotency_key_present=bool(idempotency_key),
            idempotency_key_valid=bool(idempotency_key),
            idempotency_key=idempotency_key,
            idempotency_key_recorded=bool(idempotency_key),
            duplicate_controlled_apply_detected=False,
            replay_returns_existing_apply=True,
            rollback_required=True,
            rollback_reference_created=ready,
            rollback_reference_preserved=False,
            rollback_scope="controlled_propagation_ledger",
            rollback_executed=False,
            final_event_applied_globally=False,
            existing_progress_aggregate_mutated=False,
            global_progress_mutation_applied=False,
            ranking_propagation_recorded=any(
                item.propagation_surface == "ranking" for item in controlled_entries
            ),
            retention_propagation_recorded=any(
                item.propagation_surface == "retention" for item in controlled_entries
            ),
            scheduler_propagation_recorded=any(
                item.propagation_surface == "scheduler" for item in controlled_entries
            ),
            study_cycle_propagation_recorded=any(
                item.propagation_surface == "study_cycle" for item in controlled_entries
            ),
            curriculum_graph_propagation_recorded=any(
                item.propagation_surface == "curriculum_graph"
                for item in controlled_entries
            ),
            adaptive_tuning_propagation_recorded=any(
                item.propagation_surface == "adaptive_tuning"
                for item in controlled_entries
            ),
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
            runtime_application_enabled=False,
            runtime_application_applied=False,
            commit_executed=False,
            mutation_committed=False,
            no_direct_runtime_propagation=True,
            no_new_progress_apply=True,
            no_existing_progress_aggregate_mutation=True,
            no_global_progress_mutation=True,
            no_ranking_update=True,
            no_retention_update=True,
            no_scheduler_update=True,
            no_study_cycle_update=True,
            no_curriculum_graph_update=True,
            no_adaptive_tuning_update=True,
            no_commit_execution=True,
            no_mutation_commit=True,
            no_runtime_application_beyond_minimal_ledger=True,
            no_public_answer_key_exposure=True,
            no_public_gabarito_exposure=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": CONTROLLED_PROPAGATION_APPLY_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_controlled_propagation_apply(
            result,
            user_id=user_id,
        )
        return result

    def get_controlled_propagation_apply(
        self,
        source_propagation_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledPropagationApply | None:
        return self.repository.get_simulado_controlled_propagation_apply(
            source_propagation_guardrail_id,
            user_id=user_id,
        )

    def get_controlled_propagation_apply_by_id(
        self,
        controlled_propagation_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledPropagationApply | None:
        return self.repository.get_simulado_controlled_propagation_apply_by_id(
            controlled_propagation_apply_id,
            user_id=user_id,
        )

    def _blocker_code(self, source_guardrail: SimuladoPropagationGuardrail) -> str:
        if (
            source_guardrail.answer_key_publicly_exposed
            or source_guardrail.gabarito_publicly_exposed
        ):
            return "blocked_by_public_answer_key_exposure_forbidden"
        if (
            source_guardrail.propagation_allowed_now
            or source_guardrail.propagation_applied
        ):
            return "blocked_by_source_guardrail_state_unsafe"
        if not source_guardrail.propagation_ready_for_future_review:
            return "blocked_by_guardrail_not_ready_for_future_review"
        if self._candidate_count(source_guardrail) <= 0:
            return "blocked_by_no_candidate_propagation_targets"
        if not self._idempotency_key(source_guardrail):
            return "blocked_by_idempotency_requirement_unsatisfied"
        return "controlled_propagation_ready"

    def _idempotency_key(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
    ) -> str | None:
        candidate = source_guardrail.metadata.get(
            "controlled_propagation_apply_idempotency_key"
        )
        if isinstance(candidate, str) and candidate:
            return candidate
        return f"controlled-propagation:{source_guardrail.propagation_guardrail_id}"

    def _candidate_count(self, source_guardrail: SimuladoPropagationGuardrail) -> int:
        return sum(
            len(items)
            for items in (
                source_guardrail.candidate_ranking_targets,
                source_guardrail.candidate_retention_targets,
                source_guardrail.candidate_scheduler_targets,
                source_guardrail.candidate_study_cycle_targets,
                source_guardrail.candidate_curriculum_graph_targets,
                source_guardrail.candidate_adaptive_tuning_targets,
            )
        )

    def _summary(
        self,
        *,
        source_guardrail: SimuladoPropagationGuardrail,
        candidate_count: int,
        entry_count: int,
        ready: bool,
        idempotency_key: str | None,
    ) -> ControlledPropagationApplySummary:
        return ControlledPropagationApplySummary(
            summary_id=(
                "controlled-propagation-apply-summary:"
                f"{source_guardrail.propagation_guardrail_id}"
            ),
            source_guardrail_present=True,
            source_guardrail_ready_for_future_review=(
                source_guardrail.propagation_ready_for_future_review
            ),
            source_candidate_target_count=candidate_count,
            controlled_entry_count=entry_count,
            controlled_propagation_ledger_recorded=bool(entry_count),
            controlled_propagation_successful=ready,
            direct_runtime_propagation_performed=False,
            ranking_update_performed=False,
            retention_update_performed=False,
            scheduler_update_performed=False,
            study_cycle_update_performed=False,
            curriculum_graph_update_performed=False,
            adaptive_tuning_performed=False,
            idempotency_satisfied=bool(idempotency_key),
            rollback_reference_created=ready,
            unsafe_public_answer_key_exposure_detected=(
                source_guardrail.answer_key_publicly_exposed
            ),
            unsafe_gabarito_exposure_detected=source_guardrail.gabarito_publicly_exposed,
            metadata={},
        )

    def _source_guardrail_summary(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
    ) -> ControlledPropagationSourceGuardrailSummary:
        return ControlledPropagationSourceGuardrailSummary(
            summary_id=(
                "controlled-propagation-source-guardrail-summary:"
                f"{source_guardrail.propagation_guardrail_id}"
            ),
            guardrail_mode=source_guardrail.guardrail_mode,
            guardrail_status=source_guardrail.guardrail_status,
            readiness_state=source_guardrail.readiness_state,
            propagation_ready_for_future_review=(
                source_guardrail.propagation_ready_for_future_review
            ),
            propagation_allowed_now=source_guardrail.propagation_allowed_now,
            propagation_applied=source_guardrail.propagation_applied,
            candidate_ranking_count=len(source_guardrail.candidate_ranking_targets),
            candidate_retention_count=len(source_guardrail.candidate_retention_targets),
            candidate_scheduler_count=len(source_guardrail.candidate_scheduler_targets),
            candidate_study_cycle_count=len(
                source_guardrail.candidate_study_cycle_targets
            ),
            candidate_curriculum_graph_count=len(
                source_guardrail.candidate_curriculum_graph_targets
            ),
            candidate_adaptive_tuning_count=len(
                source_guardrail.candidate_adaptive_tuning_targets
            ),
            no_propagation=source_guardrail.no_propagation,
            no_runtime_updates=(
                not source_guardrail.ranking_update_applied
                and not source_guardrail.retention_update_applied
                and not source_guardrail.scheduler_update_applied
                and not source_guardrail.study_cycle_update_applied
                and not source_guardrail.curriculum_graph_update_applied
                and not source_guardrail.adaptive_tuning_applied
            ),
            metadata={},
        )

    def _controlled_entries(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
    ) -> list[ControlledPropagationEntry]:
        entries: list[ControlledPropagationEntry] = []
        for candidate in self._all_candidates(source_guardrail):
            entries.append(
                ControlledPropagationEntry(
                    entry_id=(
                        "controlled-propagation-entry:"
                        f"{candidate.propagation_surface}:{candidate.target_id}"
                    ),
                    user_id=source_guardrail.user_id,
                    source_propagation_guardrail_id=(
                        source_guardrail.propagation_guardrail_id
                    ),
                    source_candidate_target_id=candidate.target_id,
                    source_event_record_id=candidate.source_event_record_id,
                    propagation_surface=candidate.propagation_surface,
                    propagation_kind=candidate.propagation_kind,
                    target_type=candidate.target_type,
                    target_reference=candidate.target_reference,
                    bounded_propagation_summary={
                        "source_applied_ledger_entry_id": (
                            candidate.source_applied_ledger_entry_id
                        ),
                        "propagation_surface": candidate.propagation_surface,
                        "propagation_kind": candidate.propagation_kind,
                        "target_type": candidate.target_type,
                        "candidate": candidate.candidate,
                    },
                    recorded=True,
                    applied_to_controlled_ledger=True,
                    applied_to_runtime_surface=False,
                    metadata={},
                )
            )
        return entries

    def _all_candidates(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
    ) -> list[
        CandidateRankingPropagationTarget
        | CandidateRetentionPropagationTarget
        | CandidateSchedulerPropagationTarget
        | CandidateStudyCyclePropagationTarget
        | CandidateCurriculumGraphPropagationTarget
        | CandidateAdaptiveTuningPropagationTarget
    ]:
        return [
            *source_guardrail.candidate_ranking_targets,
            *source_guardrail.candidate_retention_targets,
            *source_guardrail.candidate_scheduler_targets,
            *source_guardrail.candidate_study_cycle_targets,
            *source_guardrail.candidate_curriculum_graph_targets,
            *source_guardrail.candidate_adaptive_tuning_targets,
        ]

    def _idempotency_record(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
        idempotency_key: str | None,
    ) -> ControlledPropagationIdempotencyRecord:
        return ControlledPropagationIdempotencyRecord(
            idempotency_key_required=True,
            idempotency_key_present=bool(idempotency_key),
            idempotency_key_valid=bool(idempotency_key),
            idempotency_key=idempotency_key,
            source_propagation_guardrail_id=source_guardrail.propagation_guardrail_id,
            duplicate_controlled_apply_detected=False,
            previous_apply_id=None,
            replay_returns_existing_apply=True,
            satisfied=bool(idempotency_key),
            metadata={},
        )

    def _rollback_record(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
        ready: bool,
    ) -> ControlledPropagationRollbackRecord:
        return ControlledPropagationRollbackRecord(
            rollback_required=True,
            rollback_reference_created=ready,
            rollback_reference_preserved=False,
            rollback_scope="controlled_propagation_ledger",
            rollback_executed=False,
            rollback_summary={
                "source_propagation_guardrail_id": (
                    source_guardrail.propagation_guardrail_id
                ),
                "controlled_entries_recorded": ready,
            },
            metadata={},
        )

    def _audit_trail(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
        ready: bool,
        entry_count: int,
    ) -> list[ControlledPropagationApplyAuditEntry]:
        events = [
            (
                "controlled_propagation_apply_created",
                "Controlled propagation apply artifact created.",
            ),
            (
                "source_propagation_guardrail_evaluated",
                "Source propagation guardrail evaluated for controlled ledger recording.",
            ),
            (
                "controlled_propagation_ledger_recorded"
                if ready
                else "controlled_propagation_blocked",
                "Controlled propagation entries recorded in isolated ledger only."
                if ready
                else "Controlled propagation apply blocked.",
            ),
            (
                "controlled_propagation_not_applied_to_runtime",
                "No direct runtime propagation was performed.",
            ),
            ("no_direct_runtime_propagation", "Direct runtime propagation remains disabled."),
            ("no_new_progress_apply", "No new progress apply was created."),
            ("no_global_progress_mutation", "Global progress mutation remains disabled."),
            (
                "no_existing_progress_aggregate_mutation",
                "Existing progress aggregates remain unchanged.",
            ),
            ("no_ranking_update", "Ranking updates remain disabled."),
            ("no_retention_update", "Retention updates remain disabled."),
            ("no_scheduler_update", "Scheduler updates remain disabled."),
            ("no_study_cycle_update", "Study cycle updates remain disabled."),
            ("no_curriculum_graph_update", "Curriculum graph updates remain disabled."),
            ("no_adaptive_tuning_update", "Adaptive tuning remains disabled."),
            ("no_commit_execution", "Commit execution remains disabled."),
            ("no_mutation_commit", "Mutation commit remains disabled."),
            (
                "no_runtime_application_beyond_minimal_ledger",
                "No runtime application beyond minimal ledger remains allowed.",
            ),
        ]
        return [
            ControlledPropagationApplyAuditEntry(
                audit_id=(
                    "controlled-propagation-apply-audit:"
                    f"{source_guardrail.propagation_guardrail_id}:{index}"
                ),
                event_type=event_type,
                actor_user_id=source_guardrail.user_id,
                message=message,
                metadata={"controlled_entry_count": entry_count},
            )
            for index, (event_type, message) in enumerate(events, start=1)
        ]

    def _blockers(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
        blocker_code: str,
        ready: bool,
    ) -> list[ControlledPropagationApplyBlocker]:
        if ready:
            return []
        messages = {
            "blocked_by_source_guardrail_state_unsafe": (
                "Source propagation guardrail state is unsafe for controlled apply."
            ),
            "blocked_by_guardrail_not_ready_for_future_review": (
                "Source propagation guardrail is not ready for future review."
            ),
            "blocked_by_no_candidate_propagation_targets": (
                "No candidate propagation targets are available."
            ),
            "blocked_by_idempotency_requirement_unsatisfied": (
                "Controlled propagation idempotency requirement is unsatisfied."
            ),
            "blocked_by_public_answer_key_exposure_forbidden": (
                "Public answer key or gabarito exposure forbids controlled propagation."
            ),
        }
        return [
            ControlledPropagationApplyBlocker(
                blocker_id=(
                    "controlled-propagation-apply-blocker:"
                    f"{source_guardrail.propagation_guardrail_id}:1"
                ),
                code=blocker_code,
                message=messages.get(
                    blocker_code,
                    "Controlled propagation apply is blocked.",
                ),
                related_artifact_type="simulado_propagation_guardrail",
                related_artifact_id=source_guardrail.propagation_guardrail_id,
                metadata={},
            )
        ]

    def _validation_findings(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
        blocker_code: str,
        ready: bool,
    ) -> list[ControlledPropagationApplyValidationFinding]:
        severity = "info" if ready else "warning"
        code = (
            "controlled_propagation_apply_validated"
            if ready
            else blocker_code
        )
        message = (
            "Controlled propagation apply validated as ledger-only."
            if ready
            else "Controlled propagation apply validation detected a blocker."
        )
        return [
            ControlledPropagationApplyValidationFinding(
                finding_id=(
                    "controlled-propagation-apply-validation:"
                    f"{source_guardrail.propagation_guardrail_id}:1"
                ),
                code=code,
                severity=severity,
                message=message,
                related_artifact_type="simulado_propagation_guardrail",
                related_artifact_id=source_guardrail.propagation_guardrail_id,
                metadata={},
            )
        ]

    def _warnings(
        self,
        source_guardrail: SimuladoPropagationGuardrail,
        ready: bool,
    ) -> list[ControlledPropagationApplyWarning]:
        code = (
            "controlled_propagation_entries_recorded_to_ledger_only"
            if ready
            else "controlled_propagation_apply_not_recorded"
        )
        message = (
            "Controlled propagation entries are recorded to isolated ledger only."
            if ready
            else "Controlled propagation apply remains blocked and non-propagating."
        )
        return [
            ControlledPropagationApplyWarning(
                code=code,
                message=message,
                related_artifact_type="simulado_propagation_guardrail",
                related_artifact_id=source_guardrail.propagation_guardrail_id,
                metadata={},
            )
        ]
