from __future__ import annotations

from app.domain.models import (
    ExplicitApplyIntentApproval,
    ExplicitApplySurfaceApproval,
    RuntimeMutationAuditEntry,
    RuntimeMutationBlocker,
    RuntimeMutationRollbackPlan,
    RuntimeMutationValidationFinding,
    RuntimeMutationValidationSummary,
    RuntimeMutationWarning,
    ProposedProgressDelta,
    ProposedRuntimeSurfaceUpdate,
    SimuladoExplicitRuntimeProgressApply,
    SimuladoRuntimeProgressMutationTransaction,
)
from app.repositories.json_store import JsonStudyRepository


RUNTIME_PROGRESS_MUTATION_BUILD_METHOD = "heuristic_simulado_runtime_progress_mutation_builder"
TARGET_TYPE_BY_INTENT = {
    "progress_update_candidate": "user_progress",
    "retention_update_candidate": "subject_progress",
    "study_cycle_update_candidate": "topic_progress",
    "curriculum_graph_update_candidate": "subtopic_progress",
}
DELTA_KIND_BY_INTENT = {
    "progress_update_candidate": "mastery_delta",
    "retention_update_candidate": "review_signal_delta",
    "study_cycle_update_candidate": "completion_delta",
    "curriculum_graph_update_candidate": "confidence_delta",
}
UPDATE_KIND_BY_SURFACE = {
    "progress": "progress_delta",
    "ranking": "ranking_signal",
    "retention": "retention_signal",
    "scheduler": "scheduler_signal",
    "study_cycle": "study_cycle_signal",
    "curriculum_graph": "curriculum_graph_signal",
    "adaptive_tuning": "adaptive_tuning_signal",
}


class SimuladoRuntimeProgressMutationService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_mutation_transaction(
        self,
        source_explicit_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeProgressMutationTransaction | None:
        if user_id is None:
            return None

        explicit_apply = self.repository.get_simulado_explicit_runtime_apply_by_id(
            source_explicit_apply_id,
            user_id=user_id,
        )
        if explicit_apply is None:
            return None

        existing = self.repository.get_simulado_runtime_progress_mutation_transaction(
            source_explicit_apply_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        rollback_plan = self._rollback_plan(explicit_apply)
        proposed_progress_deltas = self._proposed_progress_deltas(explicit_apply)
        proposed_surface_updates = self._proposed_surface_updates(explicit_apply)
        blocker_codes = self._blocker_codes(
            explicit_apply=explicit_apply,
            rollback_plan=rollback_plan,
        )
        mutation_status, readiness_state = self._state(
            explicit_apply=explicit_apply,
            blocker_codes=blocker_codes,
        )
        validation_summary = self._validation_summary(
            explicit_apply=explicit_apply,
            proposed_progress_deltas=proposed_progress_deltas,
            proposed_surface_updates=proposed_surface_updates,
            rollback_plan=rollback_plan,
        )

        result = SimuladoRuntimeProgressMutationTransaction(
            mutation_transaction_id=f"simulado-progress-mutation:{explicit_apply.explicit_apply_id}",
            user_id=user_id,
            source_explicit_apply_id=explicit_apply.explicit_apply_id,
            source_apply_shell_id=explicit_apply.source_apply_shell_id,
            source_application_id=explicit_apply.source_application_id,
            source_runtime_guardrail_id=explicit_apply.source_runtime_guardrail_id,
            source_integrated_result_id=explicit_apply.source_integrated_result_id,
            source_score_result_id=explicit_apply.source_score_result_id,
            source_progress_guardrail_id=explicit_apply.source_progress_guardrail_id,
            source_attempt_session_id=explicit_apply.source_attempt_session_id,
            source_simulado_blueprint_id=explicit_apply.source_simulado_blueprint_id,
            mutation_mode="proposal_only",
            mutation_status=mutation_status,
            readiness_state=readiness_state,
            validation_summary=validation_summary,
            proposed_progress_deltas=proposed_progress_deltas,
            proposed_surface_updates=proposed_surface_updates,
            rollback_plan=rollback_plan,
            audit_trail=self._audit_trail(
                explicit_apply=explicit_apply,
                rollback_plan=rollback_plan,
                blocker_codes=blocker_codes,
                actor_user_id=user_id,
            ),
            blockers=self._blockers(explicit_apply, blocker_codes),
            validation_findings=self._findings(explicit_apply),
            warnings=self._warnings(explicit_apply),
            mutation_transaction_created=True,
            mutation_valid_for_commit=False,
            mutation_commit_ready=False,
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
            no_runtime_application=True,
            no_progress_mutation=True,
            no_ranking_update=True,
            no_retention_update=True,
            no_scheduler_update=True,
            no_study_cycle_update=True,
            no_curriculum_graph_update=True,
            no_adaptive_tuning_update=True,
            no_final_pedagogical_update_event=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": RUNTIME_PROGRESS_MUTATION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_runtime_progress_mutation_transaction(result, user_id=user_id)
        return result

    def get_mutation_transaction(
        self,
        source_explicit_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeProgressMutationTransaction | None:
        return self.repository.get_simulado_runtime_progress_mutation_transaction(
            source_explicit_apply_id,
            user_id=user_id,
        )

    def get_mutation_transaction_by_id(
        self,
        mutation_transaction_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeProgressMutationTransaction | None:
        return self.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
            mutation_transaction_id,
            user_id=user_id,
        )

    def _validation_summary(
        self,
        *,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
        proposed_progress_deltas: list[ProposedProgressDelta],
        proposed_surface_updates: list[ProposedRuntimeSurfaceUpdate],
        rollback_plan: RuntimeMutationRollbackPlan,
    ) -> RuntimeMutationValidationSummary:
        return RuntimeMutationValidationSummary(
            summary_id=f"runtime-mutation-validation:{explicit_apply.explicit_apply_id}",
            source_explicit_apply_present=True,
            explicit_apply_recorded=explicit_apply.explicit_apply_recorded,
            explicit_apply_approved=explicit_apply.explicit_apply_approved,
            approved_for_future_runtime_mutation_review=explicit_apply.decision_summary.approved_for_future_runtime_mutation_review,
            approved_for_apply_now=self._approved_for_apply_now(explicit_apply),
            apply_ready_for_runtime_mutation=explicit_apply.apply_ready_for_runtime_mutation,
            confirmations_satisfied=explicit_apply.confirmation_summary.all_confirmations_satisfied,
            proposed_delta_count=len(proposed_progress_deltas),
            proposed_surface_update_count=len(proposed_surface_updates),
            rollback_plan_available=rollback_plan.rollback_available,
            transaction_valid_for_commit=False,
            transaction_commit_ready=False,
            unsafe_public_answer_key_exposure_detected=self._unsafe_public_answer_key_exposure_detected(
                explicit_apply
            ),
            unsafe_gabarito_exposure_detected=self._unsafe_gabarito_exposure_detected(explicit_apply),
            metadata={},
        )

    def _proposed_progress_deltas(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> list[ProposedProgressDelta]:
        deltas: list[ProposedProgressDelta] = []
        for approval in explicit_apply.intent_approvals:
            target_type = TARGET_TYPE_BY_INTENT.get(approval.intent_type, "unknown")
            target_id = explicit_apply.user_id if target_type == "user_progress" else None
            blockers: list[str] = []
            if not approval.approved_for_future_runtime_mutation_review:
                blockers.append("delta_blocked_by_unapproved_intent")
            if not target_id:
                blockers.append("delta_blocked_by_missing_target")
            blockers.extend(
                [
                    "delta_blocked_by_commit_not_allowed",
                    "delta_blocked_by_missing_before_snapshot",
                    "delta_blocked_by_missing_after_snapshot",
                ]
            )
            deltas.append(
                ProposedProgressDelta(
                    delta_id=f"runtime-mutation-delta:{approval.approval_id}",
                    source_intent_approval_id=approval.approval_id,
                    target_type=target_type,
                    target_id=target_id,
                    topic_id=None,
                    subtopic_id=None,
                    microtopic_id=None,
                    subject_id=None,
                    delta_kind=DELTA_KIND_BY_INTENT.get(approval.intent_type, "unknown"),
                    before_snapshot_available=False,
                    after_snapshot_available=False,
                    proposed_before_summary={"available": False},
                    proposed_after_summary={"available": False},
                    proposed_delta_value=None,
                    confidence=0.0,
                    applied=False,
                    commit_allowed=False,
                    blockers=blockers,
                    warnings=list(approval.warnings),
                    metadata={
                        "source_explicit_apply_id": explicit_apply.explicit_apply_id,
                        "proposed_surface": approval.proposed_surface,
                    },
                )
            )
        return deltas

    def _proposed_surface_updates(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> list[ProposedRuntimeSurfaceUpdate]:
        updates: list[ProposedRuntimeSurfaceUpdate] = []
        for approval in explicit_apply.surface_approvals:
            blockers: list[str] = []
            if not approval.approved_for_future_runtime_mutation_review:
                blockers.append("surface_update_blocked_by_unapproved_surface")
            blockers.extend(
                [
                    "surface_update_blocked_by_commit_not_allowed",
                    "surface_update_blocked_by_missing_before_snapshot",
                    "surface_update_blocked_by_missing_after_snapshot",
                ]
            )
            updates.append(
                ProposedRuntimeSurfaceUpdate(
                    update_id=f"runtime-surface-update:{approval.approval_id}",
                    source_surface_approval_id=approval.approval_id,
                    surface_type=approval.surface_type,
                    surface_name=approval.surface_type,
                    update_kind=UPDATE_KIND_BY_SURFACE.get(approval.surface_type, "unknown"),
                    target_ref=approval.source_diff_id,
                    before_snapshot_available=False,
                    after_snapshot_available=False,
                    proposed_before_summary={"available": False},
                    proposed_after_summary={"available": False},
                    applied=False,
                    commit_allowed=False,
                    blockers=blockers,
                    warnings=list(approval.warnings),
                    metadata={"source_explicit_apply_id": explicit_apply.explicit_apply_id},
                )
            )
        return updates

    def _rollback_plan(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> RuntimeMutationRollbackPlan:
        available = bool(explicit_apply.metadata.get("runtime_mutation_rollback_plan_available", False))
        verified = bool(explicit_apply.metadata.get("runtime_mutation_rollback_plan_verified", False))
        steps_count = int(explicit_apply.metadata.get("runtime_mutation_rollback_steps_count", 0) or 0)
        return RuntimeMutationRollbackPlan(
            rollback_plan_id=f"runtime-mutation-rollback:{explicit_apply.explicit_apply_id}",
            rollback_required=True,
            rollback_available=available,
            rollback_verified=verified,
            rollback_summary="Rollback planning is required before any future mutation commit.",
            rollback_steps_count=steps_count,
            metadata={},
        )

    def _blocker_codes(
        self,
        *,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
        rollback_plan: RuntimeMutationRollbackPlan,
    ) -> list[str]:
        blocker_codes: list[str] = []
        if self._unsafe_public_answer_key_exposure_detected(explicit_apply) or self._unsafe_gabarito_exposure_detected(
            explicit_apply
        ):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if (
            explicit_apply.decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and explicit_apply.confirmation_summary.all_confirmations_satisfied is False
        ):
            blocker_codes.append("blocked_by_confirmations_incomplete")
        if explicit_apply.explicit_apply_approved is False:
            blocker_codes.append("blocked_by_explicit_apply_not_approved")
        if explicit_apply.explicit_apply_approved and not self._approved_for_apply_now(explicit_apply):
            blocker_codes.append("blocked_by_apply_now_not_allowed")
        if (
            explicit_apply.explicit_apply_approved
            and self._approved_for_apply_now(explicit_apply)
            and explicit_apply.apply_ready_for_runtime_mutation is False
        ):
            blocker_codes.append("blocked_by_apply_not_ready_for_runtime_mutation")
        if rollback_plan.rollback_available is False or rollback_plan.rollback_verified is False:
            blocker_codes.append("blocked_by_missing_rollback_plan")
        if any(not item.approved_for_future_runtime_mutation_review for item in explicit_apply.intent_approvals):
            blocker_codes.append("blocked_by_intents_not_approved")
        if any(not item.approved_for_future_runtime_mutation_review for item in explicit_apply.surface_approvals):
            blocker_codes.append("blocked_by_surfaces_not_approved")
        if bool(explicit_apply.metadata.get("force_runtime_mutation_disabled", False)):
            blocker_codes.append("blocked_by_runtime_mutation_disabled")
        return blocker_codes

    def _state(
        self,
        *,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
        blocker_codes: list[str],
    ) -> tuple[str, str]:
        if "blocked_by_public_answer_key_exposure_forbidden" in blocker_codes:
            return "mutation_blocked", "blocked_by_public_answer_key_exposure_forbidden"
        if "blocked_by_runtime_mutation_disabled" in blocker_codes:
            return "mutation_blocked", "blocked_by_runtime_mutation_disabled"
        if "blocked_by_confirmations_incomplete" in blocker_codes:
            return "mutation_blocked", "blocked_by_confirmations_incomplete"
        if "blocked_by_explicit_apply_not_approved" in blocker_codes:
            return "mutation_blocked", "blocked_by_explicit_apply_not_approved"
        if "blocked_by_apply_now_not_allowed" in blocker_codes:
            return "mutation_blocked", "blocked_by_apply_now_not_allowed"
        if "blocked_by_apply_not_ready_for_runtime_mutation" in blocker_codes:
            return "mutation_blocked", "blocked_by_apply_not_ready_for_runtime_mutation"
        if "blocked_by_missing_rollback_plan" in blocker_codes:
            return "mutation_blocked", "blocked_by_missing_rollback_plan"
        if "blocked_by_intents_not_approved" in blocker_codes:
            return "mutation_blocked", "blocked_by_intents_not_approved"
        if "blocked_by_surfaces_not_approved" in blocker_codes:
            return "mutation_blocked", "blocked_by_surfaces_not_approved"
        if explicit_apply.explicit_apply_approved:
            return "not_applied", "ready_for_future_mutation_commit_review"
        return "mutation_blocked", "mutation_needs_review"

    def _audit_trail(
        self,
        *,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
        rollback_plan: RuntimeMutationRollbackPlan,
        blocker_codes: list[str],
        actor_user_id: str,
    ) -> list[RuntimeMutationAuditEntry]:
        events = [
            ("mutation_transaction_created", "Runtime progress mutation transaction artifact was created."),
            ("mutation_proposal_created", "Runtime progress mutation proposal remains dry-run only."),
            ("no_runtime_application", "Runtime application remains disabled in this foundation."),
            ("no_progress_mutation", "Progress mutation remains disabled in this foundation."),
            (
                "no_final_pedagogical_update_event",
                "Final pedagogical update events remain disabled in this foundation.",
            ),
        ]
        if blocker_codes:
            events.append(("mutation_transaction_blocked", "Runtime progress mutation transaction remains blocked."))
        if "blocked_by_explicit_apply_not_approved" in blocker_codes:
            events.append(("explicit_apply_not_approved", "Explicit runtime apply is not approved for mutation review."))
        if "blocked_by_apply_now_not_allowed" in blocker_codes:
            events.append(("apply_now_not_allowed", "Apply-now execution remains forbidden in this foundation."))
        if "blocked_by_confirmations_incomplete" in blocker_codes:
            events.append(("confirmations_incomplete", "Source confirmations remain incomplete."))
        if rollback_plan.rollback_available is False or rollback_plan.rollback_verified is False:
            events.append(("rollback_plan_missing", "Rollback plan metadata remains missing or unverified."))
        return [
            RuntimeMutationAuditEntry(
                audit_id=f"runtime-progress-mutation-audit:{event_type}:{explicit_apply.explicit_apply_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blockers(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
        blocker_codes: list[str],
    ) -> list[RuntimeMutationBlocker]:
        messages = {
            "blocked_by_explicit_apply_not_approved": "Explicit runtime apply remains not approved for mutation proposal commit.",
            "blocked_by_apply_not_ready_for_runtime_mutation": "Explicit apply is not ready for runtime mutation review.",
            "blocked_by_apply_now_not_allowed": "Apply-now execution remains forbidden in this foundation.",
            "blocked_by_confirmations_incomplete": "Required confirmations remain incomplete for mutation proposal review.",
            "blocked_by_missing_rollback_plan": "Rollback plan metadata remains missing or unverified.",
            "blocked_by_intents_not_approved": "One or more source intent approvals remain not approved for future mutation review.",
            "blocked_by_surfaces_not_approved": "One or more source surface approvals remain not approved for future mutation review.",
            "blocked_by_runtime_mutation_disabled": "Runtime mutation remains disabled in this foundation.",
            "blocked_by_public_answer_key_exposure_forbidden": "Potential public answer key exposure forbids mutation proposal review.",
        }
        return [
            RuntimeMutationBlocker(
                blocker_id=f"runtime-progress-mutation-blocker:{code}:{explicit_apply.explicit_apply_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_explicit_runtime_apply",
                related_artifact_id=explicit_apply.explicit_apply_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> list[RuntimeMutationValidationFinding]:
        items = [
            RuntimeMutationValidationFinding(
                finding_id=f"runtime-progress-mutation-finding:proposal-only:{explicit_apply.explicit_apply_id}",
                code="runtime_progress_mutation_proposal_only",
                severity="info",
                message="Runtime progress mutation remains a proposal-only artifact in this foundation.",
                related_artifact_type="simulado_explicit_runtime_apply",
                related_artifact_id=explicit_apply.explicit_apply_id,
                metadata={},
            )
        ]
        for source in explicit_apply.validation_findings:
            items.append(
                RuntimeMutationValidationFinding(
                    finding_id=f"runtime-progress-mutation-finding:{source.code}:{explicit_apply.explicit_apply_id}",
                    code=source.code,
                    severity=source.severity,
                    message=source.message,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items

    def _warnings(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> list[RuntimeMutationWarning]:
        items = [
            RuntimeMutationWarning(
                code="runtime_progress_mutation_not_committed",
                message="Runtime progress mutation transaction remains non-committed in this foundation.",
                severity="warning",
                related_artifact_type="simulado_explicit_runtime_apply",
                related_artifact_id=explicit_apply.explicit_apply_id,
                metadata={},
            )
        ]
        for source in explicit_apply.warnings:
            items.append(
                RuntimeMutationWarning(
                    code=source.code,
                    message=source.message,
                    severity=source.severity,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items

    def _approved_for_apply_now(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> bool:
        return any(item.approved_for_apply_now for item in explicit_apply.intent_approvals) or any(
            item.approved_for_apply_now for item in explicit_apply.surface_approvals
        )

    def _unsafe_public_answer_key_exposure_detected(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> bool:
        return explicit_apply.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"

    def _unsafe_gabarito_exposure_detected(
        self,
        explicit_apply: SimuladoExplicitRuntimeProgressApply,
    ) -> bool:
        return explicit_apply.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
