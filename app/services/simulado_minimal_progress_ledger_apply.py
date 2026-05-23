from __future__ import annotations

from app.domain.models import (
    AppliedProgressLedgerEntry,
    MinimalProgressLedgerApplyAuditEntry,
    MinimalProgressLedgerApplyBlocker,
    MinimalProgressLedgerApplySummary,
    MinimalProgressLedgerApplyValidationFinding,
    MinimalProgressLedgerApplyWarning,
    MinimalProgressLedgerIdempotencyRecord,
    MinimalProgressLedgerRollbackRecord,
    SimuladoFinalPedagogicalUpdateEvent,
    SimuladoMinimalProgressLedgerApply,
    SimuladoRuntimeApplyPolicy,
)
from app.repositories.json_store import JsonStudyRepository


MINIMAL_PROGRESS_LEDGER_APPLY_BUILD_METHOD = (
    "heuristic_simulado_minimal_progress_ledger_apply_builder"
)


class SimuladoMinimalProgressLedgerApplyService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_minimal_progress_ledger_apply(
        self,
        source_runtime_apply_policy_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoMinimalProgressLedgerApply | None:
        if user_id is None:
            return None

        policy = self.repository.get_simulado_runtime_apply_policy_by_id(
            source_runtime_apply_policy_id,
            user_id=user_id,
        )
        if policy is None:
            return None

        existing = self.repository.get_simulado_minimal_progress_ledger_apply(
            source_runtime_apply_policy_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        final_event = self.repository.get_simulado_final_pedagogical_update_event_by_id(
            policy.source_final_event_id,
            user_id=user_id,
        )
        if final_event is None:
            return None

        blocker_code = self._blocker_code(policy, final_event)
        apply_allowed = blocker_code == "minimal_progress_ledger_apply_ready"
        idempotency_key = self._idempotency_key(policy)
        applied_ledger_entries = (
            self._applied_ledger_entries(policy, final_event, user_id=user_id)
            if apply_allowed
            else []
        )
        apply_status = (
            "minimal_ledger_apply_applied" if apply_allowed else "apply_blocked"
        )
        readiness_state = (
            "minimal_progress_ledger_apply_applied" if apply_allowed else blocker_code
        )

        result = SimuladoMinimalProgressLedgerApply(
            minimal_progress_ledger_apply_id=(
                f"simulado-minimal-progress-ledger-apply:{policy.runtime_apply_policy_id}"
            ),
            user_id=user_id,
            source_runtime_apply_policy_id=policy.runtime_apply_policy_id,
            source_final_event_id=policy.source_final_event_id,
            source_controlled_execution_id=policy.source_controlled_execution_id,
            source_execution_plan_id=policy.source_execution_plan_id,
            source_execution_approval_id=policy.source_execution_approval_id,
            source_score_result_id=policy.source_score_result_id,
            source_progress_guardrail_id=policy.source_progress_guardrail_id,
            source_integrated_result_id=policy.source_integrated_result_id,
            source_attempt_session_id=policy.source_attempt_session_id,
            source_simulado_blueprint_id=policy.source_simulado_blueprint_id,
            apply_mode="minimal_progress_ledger_apply",
            apply_status=apply_status,
            readiness_state=readiness_state,
            apply_summary=self._summary(
                policy=policy,
                final_event=final_event,
                applied_ledger_entries=applied_ledger_entries,
                apply_allowed=apply_allowed,
            ),
            applied_ledger_entries=applied_ledger_entries,
            idempotency_record=self._idempotency_record(
                policy=policy,
                final_event=final_event,
                idempotency_key=idempotency_key,
            ),
            rollback_record=self._rollback_record(policy=policy, apply_allowed=apply_allowed),
            audit_trail=self._audit_trail(
                policy=policy,
                apply_allowed=apply_allowed,
                applied_ledger_entries=applied_ledger_entries,
            ),
            blockers=self._blockers(policy=policy, blocker_code=blocker_code, apply_allowed=apply_allowed),
            validation_findings=self._validation_findings(
                policy=policy,
                blocker_code=blocker_code,
                apply_allowed=apply_allowed,
            ),
            warnings=self._warnings(policy=policy, apply_allowed=apply_allowed),
            minimal_progress_ledger_apply_created=True,
            minimal_progress_ledger_apply_allowed=apply_allowed,
            minimal_progress_ledger_apply_applied=apply_allowed,
            applied_progress_ledger_entry_created=bool(applied_ledger_entries),
            applied_progress_ledger_entry_count=len(applied_ledger_entries),
            idempotency_key_required=policy.idempotency_requirement.idempotency_key_required,
            idempotency_key_present=policy.idempotency_requirement.idempotency_key_present,
            idempotency_key_valid=policy.idempotency_requirement.idempotency_key_valid,
            idempotency_key=idempotency_key,
            idempotency_key_recorded=bool(idempotency_key)
            and policy.idempotency_requirement.satisfied,
            duplicate_apply_detected=False,
            rollback_required=policy.rollback_requirement.rollback_required,
            rollback_reference_created=policy.rollback_requirement.satisfied,
            rollback_available=policy.rollback_requirement.satisfied,
            rollback_executed=False,
            final_event_applied_to_minimal_ledger=apply_allowed,
            final_event_applied_globally=False,
            final_event_application_started=False,
            final_event_application_completed=False,
            existing_progress_aggregate_mutated=False,
            global_progress_mutation_applied=False,
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
            runtime_application_enabled=False,
            runtime_application_applied=False,
            commit_executed=False,
            mutation_committed=False,
            no_global_progress_mutation=True,
            no_existing_progress_aggregate_mutation=True,
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
                "build_method": MINIMAL_PROGRESS_LEDGER_APPLY_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_minimal_progress_ledger_apply(result, user_id=user_id)
        return result

    def get_minimal_progress_ledger_apply(
        self,
        source_runtime_apply_policy_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoMinimalProgressLedgerApply | None:
        return self.repository.get_simulado_minimal_progress_ledger_apply(
            source_runtime_apply_policy_id,
            user_id=user_id,
        )

    def get_minimal_progress_ledger_apply_by_id(
        self,
        minimal_progress_ledger_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoMinimalProgressLedgerApply | None:
        return self.repository.get_simulado_minimal_progress_ledger_apply_by_id(
            minimal_progress_ledger_apply_id,
            user_id=user_id,
        )

    def _blocker_code(
        self,
        policy: SimuladoRuntimeApplyPolicy,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
    ) -> str:
        if (
            final_event.event_summary.unsafe_public_answer_key_exposure_detected
            or final_event.event_summary.unsafe_gabarito_exposure_detected
        ):
            return "blocked_by_public_answer_key_exposure_forbidden"
        if not policy.runtime_apply_feature_flag_enabled:
            return "blocked_by_policy_feature_flag_disabled"
        if not policy.runtime_apply_allowed_now:
            return "blocked_by_runtime_apply_not_allowed_now"
        if not policy.minimal_progress_ledger_apply_allowed:
            return "blocked_by_minimal_progress_ledger_scope_not_allowed"
        if policy.final_event_applied or final_event.final_pedagogical_update_event_applied:
            return "blocked_by_final_event_already_applied"
        if not policy.idempotency_requirement.satisfied:
            return "blocked_by_idempotency_requirement_unsatisfied"
        if not policy.rollback_requirement.satisfied:
            return "blocked_by_rollback_requirement_unsatisfied"
        if not policy.audit_requirement.satisfied:
            return "blocked_by_audit_requirement_unsatisfied"
        if not policy.human_review_requirement.satisfied:
            return "blocked_by_human_review_requirement_unsatisfied"
        if not policy.environment_safety_requirement.satisfied:
            return "blocked_by_environment_not_safe_for_apply"
        if not final_event.proposed_progress_updates:
            return "blocked_by_no_proposed_progress_updates"
        return "minimal_progress_ledger_apply_ready"

    def _idempotency_key(self, policy: SimuladoRuntimeApplyPolicy) -> str | None:
        candidate = policy.metadata.get("minimal_progress_ledger_apply_idempotency_key")
        if isinstance(candidate, str) and candidate:
            return candidate
        if not policy.idempotency_requirement.idempotency_key_required:
            return None
        return f"minimal-progress-ledger:{policy.runtime_apply_policy_id}"

    def _summary(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        applied_ledger_entries: list[AppliedProgressLedgerEntry],
        apply_allowed: bool,
    ) -> MinimalProgressLedgerApplySummary:
        return MinimalProgressLedgerApplySummary(
            summary_id=f"minimal-progress-ledger-apply-summary:{policy.runtime_apply_policy_id}",
            source_policy_present=True,
            source_policy_feature_flag_enabled=policy.runtime_apply_feature_flag_enabled,
            source_policy_apply_allowed_now=policy.runtime_apply_allowed_now,
            source_minimal_progress_ledger_apply_allowed=(
                policy.minimal_progress_ledger_apply_allowed
            ),
            source_final_event_present=True,
            source_final_event_applied=final_event.final_pedagogical_update_event_applied,
            proposed_progress_update_count=len(final_event.proposed_progress_updates),
            applied_ledger_entry_count=len(applied_ledger_entries),
            duplicate_apply_detected=False,
            idempotency_satisfied=policy.idempotency_requirement.satisfied,
            rollback_reference_created=policy.rollback_requirement.satisfied,
            ledger_apply_successful=apply_allowed,
            global_progress_mutation_applied=False,
            existing_progress_aggregate_mutated=False,
            propagation_performed=False,
            unsafe_public_answer_key_exposure_detected=(
                final_event.event_summary.unsafe_public_answer_key_exposure_detected
            ),
            unsafe_gabarito_exposure_detected=(
                final_event.event_summary.unsafe_gabarito_exposure_detected
            ),
            metadata={},
        )

    def _applied_ledger_entries(
        self,
        policy: SimuladoRuntimeApplyPolicy,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        *,
        user_id: str | None,
    ) -> list[AppliedProgressLedgerEntry]:
        entries: list[AppliedProgressLedgerEntry] = []
        for item in final_event.proposed_progress_updates:
            summary = dict(item.bounded_summary)
            delta_kind = summary.get("delta_kind", "unknown")
            target_type = item.target_type
            if target_type not in {
                "simulado_attempt",
                "simulado_score",
                "simulado_completion",
                "topic_signal",
            }:
                target_type = "unknown"
            entries.append(
                AppliedProgressLedgerEntry(
                    entry_id=f"applied-progress-ledger-entry:{item.entry_id}",
                    user_id=user_id,
                    source_final_event_id=final_event.final_event_id,
                    source_policy_id=policy.runtime_apply_policy_id,
                    source_proposed_update_id=item.entry_id,
                    source_attempt_session_id=policy.source_attempt_session_id,
                    source_score_result_id=policy.source_score_result_id,
                    target_type=target_type,
                    target_id=item.target_id,
                    delta_kind=str(delta_kind),
                    bounded_delta_summary={
                        "target_type": target_type,
                        "delta_kind": str(delta_kind),
                        "proposed": item.proposed,
                        "source_record_id": item.source_record_id,
                    },
                    metadata={},
                )
            )
        return entries

    def _idempotency_record(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        idempotency_key: str | None,
    ) -> MinimalProgressLedgerIdempotencyRecord:
        return MinimalProgressLedgerIdempotencyRecord(
            idempotency_key_required=policy.idempotency_requirement.idempotency_key_required,
            idempotency_key_present=policy.idempotency_requirement.idempotency_key_present,
            idempotency_key_valid=policy.idempotency_requirement.idempotency_key_valid,
            idempotency_key=idempotency_key,
            source_policy_id=policy.runtime_apply_policy_id,
            source_final_event_id=final_event.final_event_id,
            duplicate_apply_detected=False,
            previous_apply_id=None,
            satisfied=policy.idempotency_requirement.satisfied,
            metadata={},
        )

    def _rollback_record(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        apply_allowed: bool,
    ) -> MinimalProgressLedgerRollbackRecord:
        return MinimalProgressLedgerRollbackRecord(
            rollback_required=policy.rollback_requirement.rollback_required,
            rollback_reference_created=policy.rollback_requirement.satisfied,
            rollback_available=policy.rollback_requirement.satisfied,
            rollback_executed=False,
            rollback_scope="minimal_progress_ledger",
            rollback_summary={
                "safe_reference_only": True,
                "ledger_apply_successful": apply_allowed,
            },
            metadata={},
        )

    def _audit_trail(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        apply_allowed: bool,
        applied_ledger_entries: list[AppliedProgressLedgerEntry],
    ) -> list[MinimalProgressLedgerApplyAuditEntry]:
        trail = [
            MinimalProgressLedgerApplyAuditEntry(
                audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:created",
                event_type="minimal_progress_ledger_apply_created",
                actor_user_id=policy.user_id,
                message="Minimal progress ledger apply artifact created.",
                metadata={},
            )
        ]
        if apply_allowed:
            trail.extend(
                [
                    MinimalProgressLedgerApplyAuditEntry(
                        audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:applied",
                        event_type="minimal_progress_ledger_apply_applied",
                        actor_user_id=policy.user_id,
                        message="Minimal progress ledger apply succeeded in isolated ledger scope.",
                        metadata={},
                    ),
                    MinimalProgressLedgerApplyAuditEntry(
                        audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:entries",
                        event_type="applied_progress_ledger_entry_created",
                        actor_user_id=policy.user_id,
                        message="Bounded isolated progress ledger entries were created.",
                        metadata={"entry_count": len(applied_ledger_entries)},
                    ),
                    MinimalProgressLedgerApplyAuditEntry(
                        audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:idempotency",
                        event_type="idempotency_key_recorded",
                        actor_user_id=policy.user_id,
                        message="Idempotency key was recorded for isolated ledger apply.",
                        metadata={},
                    ),
                    MinimalProgressLedgerApplyAuditEntry(
                        audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:rollback",
                        event_type="rollback_reference_created",
                        actor_user_id=policy.user_id,
                        message="Rollback reference was preserved for isolated ledger apply.",
                        metadata={},
                    ),
                ]
            )
        else:
            trail.append(
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:blocked",
                    event_type="minimal_progress_ledger_apply_blocked",
                    actor_user_id=policy.user_id,
                    message="Minimal progress ledger apply remains blocked by policy or source state.",
                    metadata={},
                )
            )
        trail.extend(
            [
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-global-progress",
                    event_type="no_global_progress_mutation",
                    actor_user_id=policy.user_id,
                    message="No global progress mutation was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-existing-aggregate",
                    event_type="no_existing_progress_aggregate_mutation",
                    actor_user_id=policy.user_id,
                    message="No existing progress aggregate was mutated.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-ranking",
                    event_type="no_ranking_update",
                    actor_user_id=policy.user_id,
                    message="No ranking update was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-retention",
                    event_type="no_retention_update",
                    actor_user_id=policy.user_id,
                    message="No retention update was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-scheduler",
                    event_type="no_scheduler_update",
                    actor_user_id=policy.user_id,
                    message="No scheduler update was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-study-cycle",
                    event_type="no_study_cycle_update",
                    actor_user_id=policy.user_id,
                    message="No study cycle update was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-graph",
                    event_type="no_curriculum_graph_update",
                    actor_user_id=policy.user_id,
                    message="No curriculum graph update was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-tuning",
                    event_type="no_adaptive_tuning_update",
                    actor_user_id=policy.user_id,
                    message="No adaptive tuning update was performed.",
                    metadata={},
                ),
                MinimalProgressLedgerApplyAuditEntry(
                    audit_id=f"minimal-progress-ledger-apply-audit:{policy.runtime_apply_policy_id}:no-runtime",
                    event_type="no_runtime_application_beyond_minimal_ledger",
                    actor_user_id=policy.user_id,
                    message="No runtime application was performed beyond the minimal ledger artifact.",
                    metadata={},
                ),
            ]
        )
        return trail

    def _blockers(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        blocker_code: str,
        apply_allowed: bool,
    ) -> list[MinimalProgressLedgerApplyBlocker]:
        if apply_allowed:
            return []
        messages = {
            "blocked_by_policy_feature_flag_disabled": "Runtime apply feature flag remains disabled.",
            "blocked_by_runtime_apply_not_allowed_now": "Runtime apply remains not allowed now.",
            "blocked_by_minimal_progress_ledger_scope_not_allowed": "Minimal progress ledger scope remains blocked.",
            "blocked_by_final_event_already_applied": "Source final event is already marked as applied.",
            "blocked_by_idempotency_requirement_unsatisfied": "Idempotency requirement remains unsatisfied.",
            "blocked_by_rollback_requirement_unsatisfied": "Rollback requirement remains unsatisfied.",
            "blocked_by_audit_requirement_unsatisfied": "Audit requirement remains unsatisfied.",
            "blocked_by_human_review_requirement_unsatisfied": "Human review requirement remains unsatisfied.",
            "blocked_by_environment_not_safe_for_apply": "Environment remains unsafe for isolated ledger apply.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key exposure prevents isolated ledger apply.",
            "blocked_by_no_proposed_progress_updates": "No proposed progress updates are available for isolated ledger apply.",
        }
        return [
            MinimalProgressLedgerApplyBlocker(
                blocker_id=f"minimal-progress-ledger-apply-blocker:{policy.runtime_apply_policy_id}:{blocker_code}",
                code=blocker_code,
                message=messages.get(blocker_code, blocker_code.replace("_", " ")),
                related_artifact_type="simulado_runtime_apply_policy",
                related_artifact_id=policy.runtime_apply_policy_id,
                metadata={},
            )
        ]

    def _validation_findings(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        blocker_code: str,
        apply_allowed: bool,
    ) -> list[MinimalProgressLedgerApplyValidationFinding]:
        return [
            MinimalProgressLedgerApplyValidationFinding(
                finding_id=f"minimal-progress-ledger-apply-finding:{policy.runtime_apply_policy_id}:state",
                code=(
                    "minimal_progress_ledger_apply_applied"
                    if apply_allowed
                    else "minimal_progress_ledger_apply_blocked"
                ),
                message=(
                    "Minimal progress ledger apply remained isolated to bounded ledger entries only."
                ),
                related_artifact_type="simulado_runtime_apply_policy",
                related_artifact_id=policy.runtime_apply_policy_id,
                metadata={"readiness_state": blocker_code},
            )
        ]

    def _warnings(
        self,
        *,
        policy: SimuladoRuntimeApplyPolicy,
        apply_allowed: bool,
    ) -> list[MinimalProgressLedgerApplyWarning]:
        warnings = [
            MinimalProgressLedgerApplyWarning(
                code="minimal_progress_ledger_apply_isolated_only",
                message=(
                    "This apply path writes only an isolated minimal progress ledger artifact and does not propagate."
                ),
                related_artifact_type="simulado_runtime_apply_policy",
                related_artifact_id=policy.runtime_apply_policy_id,
                metadata={},
            )
        ]
        if not apply_allowed:
            warnings.append(
                MinimalProgressLedgerApplyWarning(
                    code="minimal_progress_ledger_apply_blocked",
                    message="Minimal progress ledger apply remains blocked by policy or source state.",
                    related_artifact_type="simulado_runtime_apply_policy",
                    related_artifact_id=policy.runtime_apply_policy_id,
                    metadata={},
                )
            )
        return warnings
