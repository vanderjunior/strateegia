from __future__ import annotations

from app.domain.models import (
    AppliedEventDeduplicationRecord,
    AppliedEventIdempotencyRecord,
    AppliedEventLedgerAuditEntry,
    AppliedEventLedgerBlocker,
    AppliedEventLedgerSummary,
    AppliedEventLedgerValidationFinding,
    AppliedEventLedgerWarning,
    AppliedEventRecord,
    AppliedEventReplaySafetyRecord,
    AppliedEventRollbackReference,
    SimuladoAppliedEventLedger,
    SimuladoMinimalProgressLedgerApply,
)
from app.repositories.json_store import JsonStudyRepository


APPLIED_EVENT_LEDGER_BUILD_METHOD = "heuristic_simulado_applied_event_ledger_builder"


class SimuladoAppliedEventLedgerService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_applied_event_ledger(
        self,
        source_minimal_progress_ledger_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAppliedEventLedger | None:
        if user_id is None:
            return None

        source_apply = self.repository.get_simulado_minimal_progress_ledger_apply_by_id(
            source_minimal_progress_ledger_apply_id,
            user_id=user_id,
        )
        if source_apply is None:
            return None

        existing = self.repository.get_simulado_applied_event_ledger(
            source_minimal_progress_ledger_apply_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        blocker_code = self._blocker_code(source_apply)
        ready = blocker_code == "applied_event_ledger_ready"
        event_records = self._event_records(source_apply) if ready else []
        status = "ledger_recorded" if ready else "ledger_blocked"
        readiness_state = "applied_event_ledger_recorded" if ready else blocker_code
        idempotency_key = source_apply.idempotency_key

        result = SimuladoAppliedEventLedger(
            applied_event_ledger_id=(
                f"simulado-applied-event-ledger:{source_apply.minimal_progress_ledger_apply_id}"
            ),
            user_id=user_id,
            source_minimal_progress_ledger_apply_id=source_apply.minimal_progress_ledger_apply_id,
            source_runtime_apply_policy_id=source_apply.source_runtime_apply_policy_id,
            source_final_event_id=source_apply.source_final_event_id,
            source_controlled_execution_id=source_apply.source_controlled_execution_id,
            source_execution_plan_id=source_apply.source_execution_plan_id,
            source_execution_approval_id=source_apply.source_execution_approval_id,
            source_score_result_id=source_apply.source_score_result_id,
            source_progress_guardrail_id=source_apply.source_progress_guardrail_id,
            source_integrated_result_id=source_apply.source_integrated_result_id,
            source_attempt_session_id=source_apply.source_attempt_session_id,
            source_simulado_blueprint_id=source_apply.source_simulado_blueprint_id,
            ledger_mode="applied_event_ledger",
            ledger_status=status,
            readiness_state=readiness_state,
            ledger_summary=self._summary(source_apply, event_records, ready),
            applied_event_records=event_records,
            idempotency_record=self._idempotency_record(source_apply, idempotency_key),
            deduplication_record=self._deduplication_record(
                source_apply,
                idempotency_key,
                len(event_records),
            ),
            replay_safety_record=self._replay_safety_record(),
            rollback_reference=self._rollback_reference(source_apply),
            audit_trail=self._audit_trail(source_apply, ready, len(event_records)),
            blockers=self._blockers(source_apply, blocker_code, ready),
            validation_findings=self._validation_findings(source_apply, blocker_code, ready),
            warnings=self._warnings(source_apply, ready),
            applied_event_ledger_created=True,
            ledger_event_recorded=bool(event_records),
            ledger_event_count=len(event_records),
            source_minimal_progress_ledger_apply_present=True,
            source_minimal_progress_ledger_apply_applied=(
                source_apply.minimal_progress_ledger_apply_applied
            ),
            source_applied_progress_ledger_entry_count=source_apply.applied_progress_ledger_entry_count,
            idempotency_key_required=source_apply.idempotency_key_required,
            idempotency_key_present=source_apply.idempotency_key_present,
            idempotency_key_valid=source_apply.idempotency_key_valid,
            idempotency_key=idempotency_key,
            idempotency_key_recorded=(
                bool(idempotency_key)
                and source_apply.idempotency_key_present
                and source_apply.idempotency_key_valid
            ),
            deduplication_enforced=True,
            duplicate_event_detected=False,
            duplicate_source_apply_detected=False,
            previous_ledger_id=None,
            replay_safe=True,
            replay_count=0,
            replay_returns_existing_ledger=True,
            rollback_required=source_apply.rollback_required,
            rollback_reference_preserved=source_apply.rollback_reference_created,
            rollback_executed=False,
            minimal_progress_ledger_apply_applied=source_apply.minimal_progress_ledger_apply_applied,
            applied_progress_ledger_entry_created=source_apply.applied_progress_ledger_entry_created,
            final_event_applied_to_minimal_ledger=source_apply.final_event_applied_to_minimal_ledger,
            final_event_applied_globally=False,
            existing_progress_aggregate_mutated=False,
            global_progress_mutation_applied=False,
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
            no_propagation=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": APPLIED_EVENT_LEDGER_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_applied_event_ledger(result, user_id=user_id)
        return result

    def get_applied_event_ledger(
        self,
        source_minimal_progress_ledger_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAppliedEventLedger | None:
        return self.repository.get_simulado_applied_event_ledger(
            source_minimal_progress_ledger_apply_id,
            user_id=user_id,
        )

    def get_applied_event_ledger_by_id(
        self,
        applied_event_ledger_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAppliedEventLedger | None:
        return self.repository.get_simulado_applied_event_ledger_by_id(
            applied_event_ledger_id,
            user_id=user_id,
        )

    def _blocker_code(self, source_apply: SimuladoMinimalProgressLedgerApply) -> str:
        if source_apply.answer_key_publicly_exposed or source_apply.gabarito_publicly_exposed:
            return "blocked_by_public_answer_key_exposure_forbidden"
        if not source_apply.minimal_progress_ledger_apply_applied:
            return "blocked_by_source_apply_not_applied"
        if source_apply.applied_progress_ledger_entry_count <= 0 or not source_apply.applied_ledger_entries:
            return "blocked_by_no_source_applied_entries"
        if source_apply.idempotency_key_required and not source_apply.idempotency_key_present:
            return "blocked_by_idempotency_key_missing"
        if source_apply.idempotency_key_required and not source_apply.idempotency_key_valid:
            return "blocked_by_idempotency_key_invalid"
        return "applied_event_ledger_ready"

    def _summary(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        event_records: list[AppliedEventRecord],
        ready: bool,
    ) -> AppliedEventLedgerSummary:
        return AppliedEventLedgerSummary(
            summary_id=f"applied-event-ledger-summary:{source_apply.minimal_progress_ledger_apply_id}",
            source_apply_present=True,
            source_apply_applied=source_apply.minimal_progress_ledger_apply_applied,
            source_apply_status=source_apply.apply_status,
            source_applied_entry_count=source_apply.applied_progress_ledger_entry_count,
            ledger_event_count=len(event_records),
            idempotency_satisfied=(
                source_apply.idempotency_key_present and source_apply.idempotency_key_valid
            ),
            deduplication_enforced=True,
            duplicate_event_detected=False,
            replay_safe=True,
            rollback_reference_preserved=source_apply.rollback_reference_created,
            propagation_performed=False,
            global_progress_mutation_applied=False,
            existing_progress_aggregate_mutated=False,
            unsafe_public_answer_key_exposure_detected=source_apply.answer_key_publicly_exposed,
            unsafe_gabarito_exposure_detected=source_apply.gabarito_publicly_exposed,
            metadata={"recorded": ready},
        )

    def _event_records(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
    ) -> list[AppliedEventRecord]:
        records: list[AppliedEventRecord] = []
        for item in source_apply.applied_ledger_entries:
            records.append(
                AppliedEventRecord(
                    event_record_id=f"applied-event-record:{item.entry_id}",
                    user_id=source_apply.user_id,
                    source_minimal_progress_ledger_apply_id=(
                        source_apply.minimal_progress_ledger_apply_id
                    ),
                    source_runtime_apply_policy_id=source_apply.source_runtime_apply_policy_id,
                    source_final_event_id=source_apply.source_final_event_id,
                    source_applied_progress_ledger_entry_id=item.entry_id,
                    event_type="minimal_progress_ledger_apply_recorded",
                    event_scope="minimal_progress_ledger",
                    target_type=item.target_type,
                    target_id=item.target_id,
                    bounded_event_summary={
                        "entry_type": item.entry_type,
                        "delta_kind": item.delta_kind,
                        "applied_scope": item.applied_scope,
                        "source_proposed_update_id": item.source_proposed_update_id,
                    },
                    recorded=True,
                    applied_elsewhere=False,
                    metadata={},
                )
            )
        return records

    def _idempotency_record(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        idempotency_key: str | None,
    ) -> AppliedEventIdempotencyRecord:
        return AppliedEventIdempotencyRecord(
            idempotency_key_required=source_apply.idempotency_key_required,
            idempotency_key_present=source_apply.idempotency_key_present,
            idempotency_key_valid=source_apply.idempotency_key_valid,
            idempotency_key=idempotency_key,
            source_minimal_progress_ledger_apply_id=source_apply.minimal_progress_ledger_apply_id,
            source_runtime_apply_policy_id=source_apply.source_runtime_apply_policy_id,
            duplicate_event_detected=False,
            previous_ledger_id=None,
            satisfied=(
                (not source_apply.idempotency_key_required)
                or (
                    source_apply.idempotency_key_present
                    and source_apply.idempotency_key_valid
                )
            ),
            metadata={},
        )

    def _deduplication_record(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        idempotency_key: str | None,
        event_count: int,
    ) -> AppliedEventDeduplicationRecord:
        return AppliedEventDeduplicationRecord(
            deduplication_enforced=True,
            deduplication_key=(
                f"{source_apply.minimal_progress_ledger_apply_id}:{idempotency_key or 'missing'}"
            ),
            duplicate_source_apply_detected=False,
            duplicate_event_detected=False,
            previous_ledger_id=None,
            event_count_after_deduplication=event_count,
            metadata={},
        )

    def _replay_safety_record(self) -> AppliedEventReplaySafetyRecord:
        return AppliedEventReplaySafetyRecord(
            replay_safe=True,
            replay_count=0,
            replay_returns_existing_ledger=True,
            same_source_same_key_idempotent=True,
            no_duplicate_event_records=True,
            metadata={},
        )

    def _rollback_reference(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
    ) -> AppliedEventRollbackReference:
        return AppliedEventRollbackReference(
            rollback_required=source_apply.rollback_required,
            rollback_reference_preserved=source_apply.rollback_reference_created,
            rollback_scope="minimal_progress_ledger",
            rollback_executed=False,
            rollback_summary=dict(source_apply.rollback_record.rollback_summary),
            metadata={},
        )

    def _audit_trail(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        ready: bool,
        event_count: int,
    ) -> list[AppliedEventLedgerAuditEntry]:
        trail = [
            AppliedEventLedgerAuditEntry(
                audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:created",
                event_type="applied_event_ledger_created",
                actor_user_id=source_apply.user_id,
                message="Applied event ledger artifact created.",
                metadata={},
            )
        ]
        if ready:
            trail.extend(
                [
                    AppliedEventLedgerAuditEntry(
                        audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:recorded",
                        event_type="applied_event_recorded",
                        actor_user_id=source_apply.user_id,
                        message="Applied event records were recorded from the isolated minimal ledger apply.",
                        metadata={"event_count": event_count},
                    ),
                    AppliedEventLedgerAuditEntry(
                        audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:idempotency",
                        event_type="idempotency_key_recorded",
                        actor_user_id=source_apply.user_id,
                        message="Idempotency key was recorded for the applied event ledger.",
                        metadata={},
                    ),
                    AppliedEventLedgerAuditEntry(
                        audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:dedup",
                        event_type="deduplication_enforced",
                        actor_user_id=source_apply.user_id,
                        message="Deduplication was enforced for the applied event ledger.",
                        metadata={},
                    ),
                    AppliedEventLedgerAuditEntry(
                        audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:replay",
                        event_type="replay_safe",
                        actor_user_id=source_apply.user_id,
                        message="Replay safety is enforced for the applied event ledger.",
                        metadata={},
                    ),
                ]
            )
            if source_apply.rollback_reference_created:
                trail.append(
                    AppliedEventLedgerAuditEntry(
                        audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:rollback",
                        event_type="rollback_reference_preserved",
                        actor_user_id=source_apply.user_id,
                        message="Rollback reference was preserved from the source apply artifact.",
                        metadata={},
                    )
                )
        else:
            trail.append(
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:blocked",
                    event_type="applied_event_ledger_blocked",
                    actor_user_id=source_apply.user_id,
                    message="Applied event ledger remains blocked by source state or safety rules.",
                    metadata={},
                )
            )
        trail.extend(
            [
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-new-apply",
                    event_type="no_new_progress_apply",
                    actor_user_id=source_apply.user_id,
                    message="No new progress apply was created.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-global-progress",
                    event_type="no_global_progress_mutation",
                    actor_user_id=source_apply.user_id,
                    message="No global progress mutation was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-existing-aggregate",
                    event_type="no_existing_progress_aggregate_mutation",
                    actor_user_id=source_apply.user_id,
                    message="No existing progress aggregate was mutated.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-ranking",
                    event_type="no_ranking_update",
                    actor_user_id=source_apply.user_id,
                    message="No ranking update was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-retention",
                    event_type="no_retention_update",
                    actor_user_id=source_apply.user_id,
                    message="No retention update was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-scheduler",
                    event_type="no_scheduler_update",
                    actor_user_id=source_apply.user_id,
                    message="No scheduler update was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-study-cycle",
                    event_type="no_study_cycle_update",
                    actor_user_id=source_apply.user_id,
                    message="No study cycle update was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-graph",
                    event_type="no_curriculum_graph_update",
                    actor_user_id=source_apply.user_id,
                    message="No curriculum graph update was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-tuning",
                    event_type="no_adaptive_tuning_update",
                    actor_user_id=source_apply.user_id,
                    message="No adaptive tuning update was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-commit",
                    event_type="no_commit_execution",
                    actor_user_id=source_apply.user_id,
                    message="No commit execution was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-mutation",
                    event_type="no_mutation_commit",
                    actor_user_id=source_apply.user_id,
                    message="No mutation commit was performed.",
                    metadata={},
                ),
                AppliedEventLedgerAuditEntry(
                    audit_id=f"applied-event-ledger-audit:{source_apply.minimal_progress_ledger_apply_id}:no-runtime",
                    event_type="no_runtime_application_beyond_minimal_ledger",
                    actor_user_id=source_apply.user_id,
                    message="No runtime application was performed beyond the minimal ledger layer.",
                    metadata={},
                ),
            ]
        )
        return trail

    def _blockers(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        blocker_code: str,
        ready: bool,
    ) -> list[AppliedEventLedgerBlocker]:
        if ready:
            return []
        messages = {
            "blocked_by_source_apply_not_applied": "Source minimal progress ledger apply is not applied.",
            "blocked_by_no_source_applied_entries": "Source minimal progress ledger apply has no applied entries to record.",
            "blocked_by_idempotency_key_missing": "Source minimal progress ledger apply is missing the required idempotency key.",
            "blocked_by_idempotency_key_invalid": "Source minimal progress ledger apply has an invalid idempotency key.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key exposure prevents applied event recording.",
        }
        return [
            AppliedEventLedgerBlocker(
                blocker_id=f"applied-event-ledger-blocker:{source_apply.minimal_progress_ledger_apply_id}:{blocker_code}",
                code=blocker_code,
                message=messages.get(blocker_code, blocker_code.replace("_", " ")),
                related_artifact_type="simulado_minimal_progress_ledger_apply",
                related_artifact_id=source_apply.minimal_progress_ledger_apply_id,
                metadata={},
            )
        ]

    def _validation_findings(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        blocker_code: str,
        ready: bool,
    ) -> list[AppliedEventLedgerValidationFinding]:
        return [
            AppliedEventLedgerValidationFinding(
                finding_id=f"applied-event-ledger-finding:{source_apply.minimal_progress_ledger_apply_id}:state",
                code="applied_event_ledger_recorded" if ready else "applied_event_ledger_blocked",
                message="Applied event ledger remains an audit/idempotency layer only.",
                related_artifact_type="simulado_minimal_progress_ledger_apply",
                related_artifact_id=source_apply.minimal_progress_ledger_apply_id,
                metadata={"readiness_state": blocker_code},
            )
        ]

    def _warnings(
        self,
        source_apply: SimuladoMinimalProgressLedgerApply,
        ready: bool,
    ) -> list[AppliedEventLedgerWarning]:
        warnings = [
            AppliedEventLedgerWarning(
                code="applied_event_ledger_no_propagation",
                message="This applied event ledger records isolated apply state only and does not propagate.",
                related_artifact_type="simulado_minimal_progress_ledger_apply",
                related_artifact_id=source_apply.minimal_progress_ledger_apply_id,
                metadata={},
            )
        ]
        if not ready:
            warnings.append(
                AppliedEventLedgerWarning(
                    code="applied_event_ledger_blocked",
                    message="Applied event ledger remains blocked by source apply state or idempotency safety.",
                    related_artifact_type="simulado_minimal_progress_ledger_apply",
                    related_artifact_id=source_apply.minimal_progress_ledger_apply_id,
                    metadata={},
                )
            )
        return warnings
