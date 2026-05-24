from __future__ import annotations

from app.domain.models import (
    AppliedEventRecord,
    CandidateAdaptiveTuningPropagationTarget,
    CandidateCurriculumGraphPropagationTarget,
    CandidateRankingPropagationTarget,
    CandidateRetentionPropagationTarget,
    CandidateSchedulerPropagationTarget,
    CandidateStudyCyclePropagationTarget,
    PropagationGuardrailAuditEntry,
    PropagationGuardrailBlocker,
    PropagationGuardrailValidationFinding,
    PropagationGuardrailWarning,
    PropagationReadinessSummary,
    PropagationSurfaceRiskSummary,
    SimuladoAppliedEventLedger,
    SimuladoPropagationGuardrail,
    SourceAppliedLedgerPropagationSummary,
)
from app.repositories.json_store import JsonStudyRepository


PROPAGATION_GUARDRAIL_BUILD_METHOD = "heuristic_simulado_propagation_guardrail_builder"


class SimuladoPropagationGuardrailService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_propagation_guardrail(
        self,
        source_applied_event_ledger_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoPropagationGuardrail | None:
        if user_id is None:
            return None

        source_ledger = self.repository.get_simulado_applied_event_ledger_by_id(
            source_applied_event_ledger_id,
            user_id=user_id,
        )
        if source_ledger is None:
            return None

        existing = self.repository.get_simulado_propagation_guardrail(
            source_applied_event_ledger_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        blocker_code = self._blocker_code(source_ledger)
        ready = blocker_code == "propagation_ready_for_future_review"
        candidate_ranking_targets = (
            self._ranking_targets(source_ledger) if ready else []
        )
        candidate_retention_targets = (
            self._retention_targets(source_ledger) if ready else []
        )
        candidate_scheduler_targets = (
            self._scheduler_targets(source_ledger) if ready else []
        )
        candidate_study_cycle_targets = (
            self._study_cycle_targets(source_ledger) if ready else []
        )
        candidate_curriculum_graph_targets = (
            self._curriculum_graph_targets(source_ledger) if ready else []
        )
        candidate_adaptive_tuning_targets = (
            self._adaptive_tuning_targets(source_ledger) if ready else []
        )
        status = "propagation_ready_for_future_review" if ready else "propagation_blocked"

        result = SimuladoPropagationGuardrail(
            propagation_guardrail_id=(
                f"simulado-propagation-guardrail:{source_ledger.applied_event_ledger_id}"
            ),
            user_id=user_id,
            source_applied_event_ledger_id=source_ledger.applied_event_ledger_id,
            source_minimal_progress_ledger_apply_id=source_ledger.source_minimal_progress_ledger_apply_id,
            source_runtime_apply_policy_id=source_ledger.source_runtime_apply_policy_id,
            source_final_event_id=source_ledger.source_final_event_id,
            source_controlled_execution_id=source_ledger.source_controlled_execution_id,
            source_execution_plan_id=source_ledger.source_execution_plan_id,
            source_execution_approval_id=source_ledger.source_execution_approval_id,
            source_score_result_id=source_ledger.source_score_result_id,
            source_progress_guardrail_id=source_ledger.source_progress_guardrail_id,
            source_integrated_result_id=source_ledger.source_integrated_result_id,
            source_attempt_session_id=source_ledger.source_attempt_session_id,
            source_simulado_blueprint_id=source_ledger.source_simulado_blueprint_id,
            guardrail_mode="propagation_guardrail_only",
            guardrail_status=status,
            readiness_state=blocker_code,
            readiness_summary=self._readiness_summary(
                source_ledger=source_ledger,
                ranking_count=len(candidate_ranking_targets),
                retention_count=len(candidate_retention_targets),
                scheduler_count=len(candidate_scheduler_targets),
                study_cycle_count=len(candidate_study_cycle_targets),
                curriculum_graph_count=len(candidate_curriculum_graph_targets),
                adaptive_tuning_count=len(candidate_adaptive_tuning_targets),
                ready=ready,
            ),
            source_ledger_summary=self._source_ledger_summary(source_ledger),
            candidate_ranking_targets=candidate_ranking_targets,
            candidate_retention_targets=candidate_retention_targets,
            candidate_scheduler_targets=candidate_scheduler_targets,
            candidate_study_cycle_targets=candidate_study_cycle_targets,
            candidate_curriculum_graph_targets=candidate_curriculum_graph_targets,
            candidate_adaptive_tuning_targets=candidate_adaptive_tuning_targets,
            surface_risk_summary=self._surface_risk_summary(
                ranking_count=len(candidate_ranking_targets),
                retention_count=len(candidate_retention_targets),
                scheduler_count=len(candidate_scheduler_targets),
                study_cycle_count=len(candidate_study_cycle_targets),
                curriculum_graph_count=len(candidate_curriculum_graph_targets),
                adaptive_tuning_count=len(candidate_adaptive_tuning_targets),
            ),
            audit_trail=self._audit_trail(source_ledger, ready),
            blockers=self._blockers(source_ledger, blocker_code, ready),
            validation_findings=self._validation_findings(source_ledger, ready),
            warnings=self._warnings(source_ledger, ready),
            propagation_guardrail_created=True,
            propagation_allowed_now=False,
            propagation_applied=False,
            propagation_ready_for_future_review=ready,
            ranking_propagation_allowed=False,
            ranking_update_enabled=False,
            ranking_update_applied=False,
            retention_propagation_allowed=False,
            retention_update_enabled=False,
            retention_update_applied=False,
            scheduler_propagation_allowed=False,
            scheduler_update_enabled=False,
            scheduler_update_applied=False,
            study_cycle_propagation_allowed=False,
            study_cycle_update_enabled=False,
            study_cycle_update_applied=False,
            curriculum_graph_propagation_allowed=False,
            curriculum_graph_update_enabled=False,
            curriculum_graph_update_applied=False,
            adaptive_tuning_propagation_allowed=False,
            adaptive_tuning_enabled=False,
            adaptive_tuning_applied=False,
            source_ledger_present=True,
            source_ledger_recorded=source_ledger.ledger_event_recorded,
            source_ledger_event_count=source_ledger.ledger_event_count,
            source_ledger_replay_safe=source_ledger.replay_safe,
            source_ledger_deduplication_enforced=source_ledger.deduplication_enforced,
            source_ledger_no_propagation=source_ledger.no_propagation,
            final_event_applied_globally=False,
            existing_progress_aggregate_mutated=False,
            global_progress_mutation_applied=False,
            no_new_progress_apply=True,
            no_existing_progress_aggregate_mutation=True,
            no_global_progress_mutation=True,
            no_propagation=True,
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
            commit_executed=False,
            mutation_committed=False,
            runtime_application_enabled=False,
            runtime_application_applied=False,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": PROPAGATION_GUARDRAIL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_propagation_guardrail(result, user_id=user_id)
        return result

    def get_propagation_guardrail(
        self,
        source_applied_event_ledger_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoPropagationGuardrail | None:
        return self.repository.get_simulado_propagation_guardrail(
            source_applied_event_ledger_id,
            user_id=user_id,
        )

    def get_propagation_guardrail_by_id(
        self,
        propagation_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoPropagationGuardrail | None:
        return self.repository.get_simulado_propagation_guardrail_by_id(
            propagation_guardrail_id,
            user_id=user_id,
        )

    def _blocker_code(self, source_ledger: SimuladoAppliedEventLedger) -> str:
        if source_ledger.answer_key_publicly_exposed or source_ledger.gabarito_publicly_exposed:
            return "blocked_by_public_answer_key_exposure_forbidden"
        if not source_ledger.ledger_event_recorded:
            return "blocked_by_source_ledger_not_recorded"
        if source_ledger.ledger_event_count <= 0 or not source_ledger.applied_event_records:
            return "blocked_by_no_source_event_records"
        if not source_ledger.replay_safe:
            return "blocked_by_source_ledger_not_replay_safe"
        if not source_ledger.deduplication_enforced:
            return "blocked_by_source_ledger_deduplication_missing"
        if not source_ledger.no_propagation:
            return "blocked_by_source_ledger_propagation_state_unsafe"
        if source_ledger.final_event_applied_globally:
            return "blocked_by_final_event_already_globally_applied"
        if (
            source_ledger.global_progress_mutation_applied
            or source_ledger.existing_progress_aggregate_mutated
        ):
            return "blocked_by_source_progress_mutation_detected"
        return "propagation_ready_for_future_review"

    def _readiness_summary(
        self,
        *,
        source_ledger: SimuladoAppliedEventLedger,
        ranking_count: int,
        retention_count: int,
        scheduler_count: int,
        study_cycle_count: int,
        curriculum_graph_count: int,
        adaptive_tuning_count: int,
        ready: bool,
    ) -> PropagationReadinessSummary:
        return PropagationReadinessSummary(
            summary_id=f"propagation-readiness:{source_ledger.applied_event_ledger_id}",
            source_ledger_present=True,
            source_ledger_recorded=source_ledger.ledger_event_recorded,
            source_ledger_event_count=source_ledger.ledger_event_count,
            source_ledger_replay_safe=source_ledger.replay_safe,
            source_ledger_deduplication_enforced=source_ledger.deduplication_enforced,
            source_ledger_no_propagation=source_ledger.no_propagation,
            source_final_event_applied_globally=source_ledger.final_event_applied_globally,
            source_global_progress_mutation_applied=source_ledger.global_progress_mutation_applied,
            propagation_allowed_now=False,
            propagation_ready_for_future_review=ready,
            ranking_candidate_count=ranking_count,
            retention_candidate_count=retention_count,
            scheduler_candidate_count=scheduler_count,
            study_cycle_candidate_count=study_cycle_count,
            curriculum_graph_candidate_count=curriculum_graph_count,
            adaptive_tuning_candidate_count=adaptive_tuning_count,
            blocked_surface_count=6 if ready else 0,
            unsafe_public_answer_key_exposure_detected=source_ledger.answer_key_publicly_exposed,
            unsafe_gabarito_exposure_detected=source_ledger.gabarito_publicly_exposed,
            metadata={},
        )

    def _source_ledger_summary(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> SourceAppliedLedgerPropagationSummary:
        return SourceAppliedLedgerPropagationSummary(
            summary_id=f"source-ledger-summary:{source_ledger.applied_event_ledger_id}",
            source_apply_present=source_ledger.source_minimal_progress_ledger_apply_present,
            source_apply_applied=source_ledger.source_minimal_progress_ledger_apply_applied,
            source_apply_status=source_ledger.ledger_summary.source_apply_status,
            source_applied_entry_count=source_ledger.source_applied_progress_ledger_entry_count,
            ledger_event_count=source_ledger.ledger_event_count,
            replay_safe=source_ledger.replay_safe,
            deduplication_enforced=source_ledger.deduplication_enforced,
            no_propagation=source_ledger.no_propagation,
            final_event_applied_globally=source_ledger.final_event_applied_globally,
            global_progress_mutation_applied=source_ledger.global_progress_mutation_applied,
            existing_progress_aggregate_mutated=source_ledger.existing_progress_aggregate_mutated,
            metadata={},
        )

    def _surface_risk_summary(
        self,
        *,
        ranking_count: int,
        retention_count: int,
        scheduler_count: int,
        study_cycle_count: int,
        curriculum_graph_count: int,
        adaptive_tuning_count: int,
    ) -> PropagationSurfaceRiskSummary:
        candidate_surface_count = sum(
            1
            for count in (
                ranking_count,
                retention_count,
                scheduler_count,
                study_cycle_count,
                curriculum_graph_count,
                adaptive_tuning_count,
            )
            if count > 0
        )
        return PropagationSurfaceRiskSummary(
            risk_summary_id="propagation-surface-risk-summary",
            candidate_surface_count=candidate_surface_count,
            blocked_surface_count=candidate_surface_count,
            ranking_candidate_count=ranking_count,
            retention_candidate_count=retention_count,
            scheduler_candidate_count=scheduler_count,
            study_cycle_candidate_count=study_cycle_count,
            curriculum_graph_candidate_count=curriculum_graph_count,
            adaptive_tuning_candidate_count=adaptive_tuning_count,
            propagation_allowed_surface_count=0,
            propagated_surface_count=0,
            high_risk_surface_count=candidate_surface_count,
            no_propagation=True,
            metadata={},
        )

    def _candidate_payload(
        self,
        record: AppliedEventRecord,
        *,
        surface: str,
        kind: str,
    ) -> dict[str, object]:
        return {
            "target_id": f"{surface}-candidate:{record.event_record_id}",
            "source_event_record_id": record.event_record_id,
            "source_applied_ledger_entry_id": record.source_applied_progress_ledger_entry_id,
            "propagation_surface": surface,
            "propagation_kind": kind,
            "target_type": record.target_type,
            "target_reference": record.target_id,
            "bounded_signal_summary": {
                "event_type": record.event_type,
                "target_type": record.target_type,
                "target_reference": record.target_id,
                "source_entry_id": record.source_applied_progress_ledger_entry_id,
            },
            "candidate": True,
            "propagation_allowed": False,
            "propagated": False,
            "blockers": ["propagation_blocked_by_guardrail_only_mode"],
            "warnings": ["future_review_required_before_controlled_propagation_apply"],
            "metadata": {},
        }

    def _ranking_targets(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> list[CandidateRankingPropagationTarget]:
        return [
            CandidateRankingPropagationTarget.model_validate(
                self._candidate_payload(
                    record,
                    surface="ranking",
                    kind="ranking_signal_candidate",
                )
            )
            for record in source_ledger.applied_event_records
        ]

    def _retention_targets(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> list[CandidateRetentionPropagationTarget]:
        return [
            CandidateRetentionPropagationTarget.model_validate(
                self._candidate_payload(
                    record,
                    surface="retention",
                    kind="retention_signal_candidate",
                )
            )
            for record in source_ledger.applied_event_records
        ]

    def _scheduler_targets(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> list[CandidateSchedulerPropagationTarget]:
        return [
            CandidateSchedulerPropagationTarget.model_validate(
                self._candidate_payload(
                    record,
                    surface="scheduler",
                    kind="scheduler_signal_candidate",
                )
            )
            for record in source_ledger.applied_event_records
        ]

    def _study_cycle_targets(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> list[CandidateStudyCyclePropagationTarget]:
        return [
            CandidateStudyCyclePropagationTarget.model_validate(
                self._candidate_payload(
                    record,
                    surface="study_cycle",
                    kind="study_cycle_signal_candidate",
                )
            )
            for record in source_ledger.applied_event_records
        ]

    def _curriculum_graph_targets(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> list[CandidateCurriculumGraphPropagationTarget]:
        return [
            CandidateCurriculumGraphPropagationTarget.model_validate(
                self._candidate_payload(
                    record,
                    surface="curriculum_graph",
                    kind="curriculum_graph_signal_candidate",
                )
            )
            for record in source_ledger.applied_event_records
        ]

    def _adaptive_tuning_targets(
        self,
        source_ledger: SimuladoAppliedEventLedger,
    ) -> list[CandidateAdaptiveTuningPropagationTarget]:
        return [
            CandidateAdaptiveTuningPropagationTarget.model_validate(
                self._candidate_payload(
                    record,
                    surface="adaptive_tuning",
                    kind="adaptive_tuning_signal_candidate",
                )
            )
            for record in source_ledger.applied_event_records
        ]

    def _audit_trail(
        self,
        source_ledger: SimuladoAppliedEventLedger,
        ready: bool,
    ) -> list[PropagationGuardrailAuditEntry]:
        events = [
            ("propagation_guardrail_created", "Propagation guardrail artifact created."),
            (
                "source_applied_event_ledger_evaluated",
                "Source applied event ledger evaluated for future propagation readiness.",
            ),
            (
                "propagation_ready_for_future_review" if ready else "propagation_blocked",
                "Propagation remains blocked from execution and is limited to readiness evaluation.",
            ),
            ("no_propagation", "No propagation is performed by this guardrail foundation."),
            ("no_new_progress_apply", "No new progress apply is created by this guardrail foundation."),
            (
                "no_global_progress_mutation",
                "No global progress mutation is performed by this guardrail foundation.",
            ),
            (
                "no_existing_progress_aggregate_mutation",
                "Existing progress aggregates remain unchanged.",
            ),
            ("no_ranking_update", "Ranking propagation remains disabled."),
            ("no_retention_update", "Retention propagation remains disabled."),
            ("no_scheduler_update", "Scheduler propagation remains disabled."),
            ("no_study_cycle_update", "Study cycle propagation remains disabled."),
            (
                "no_curriculum_graph_update",
                "Curriculum graph propagation remains disabled.",
            ),
            ("no_adaptive_tuning_update", "Adaptive tuning propagation remains disabled."),
            ("no_commit_execution", "Commit execution remains disabled."),
            ("no_mutation_commit", "Mutation commit remains disabled."),
            (
                "no_runtime_application_beyond_minimal_ledger",
                "Runtime application beyond the minimal ledger remains disabled.",
            ),
        ]
        return [
            PropagationGuardrailAuditEntry(
                audit_id=f"propagation-guardrail-audit:{index}:{source_ledger.applied_event_ledger_id}",
                event_type=event_type,
                actor_user_id=source_ledger.user_id,
                message=message,
                metadata={},
            )
            for index, (event_type, message) in enumerate(events, start=1)
        ]

    def _blockers(
        self,
        source_ledger: SimuladoAppliedEventLedger,
        blocker_code: str,
        ready: bool,
    ) -> list[PropagationGuardrailBlocker]:
        if ready:
            return []
        messages = {
            "blocked_by_source_ledger_not_recorded": "Source applied event ledger is not recorded and cannot be used for propagation readiness review.",
            "blocked_by_no_source_event_records": "Source applied event ledger has no recorded event rows for propagation readiness review.",
            "blocked_by_source_ledger_not_replay_safe": "Source applied event ledger is not replay safe.",
            "blocked_by_source_ledger_deduplication_missing": "Source applied event ledger is missing deduplication enforcement.",
            "blocked_by_source_ledger_propagation_state_unsafe": "Source applied event ledger indicates unsafe propagation state.",
            "blocked_by_final_event_already_globally_applied": "Final event is already marked as globally applied.",
            "blocked_by_source_progress_mutation_detected": "Source ledger indicates progress mutation outside the isolated ledger boundary.",
            "blocked_by_public_answer_key_exposure_forbidden": "Public answer key and gabarito exposure remain forbidden.",
        }
        return [
            PropagationGuardrailBlocker(
                blocker_id=f"propagation-guardrail-blocker:{blocker_code}:{source_ledger.applied_event_ledger_id}",
                code=blocker_code,
                message=messages.get(blocker_code, "Propagation is blocked."),
                related_artifact_type="simulado_applied_event_ledger",
                related_artifact_id=source_ledger.applied_event_ledger_id,
                metadata={},
            )
        ]

    def _validation_findings(
        self,
        source_ledger: SimuladoAppliedEventLedger,
        ready: bool,
    ) -> list[PropagationGuardrailValidationFinding]:
        return [
            PropagationGuardrailValidationFinding(
                finding_id=f"propagation-guardrail-finding:{source_ledger.applied_event_ledger_id}",
                code=(
                    "source_ledger_ready_for_future_review"
                    if ready
                    else "source_ledger_blocked_for_propagation_review"
                ),
                message=(
                    "Source applied event ledger is safe for future propagation review."
                    if ready
                    else "Source applied event ledger is blocked for propagation review."
                ),
                related_artifact_type="simulado_applied_event_ledger",
                related_artifact_id=source_ledger.applied_event_ledger_id,
                metadata={"source_event_count": source_ledger.ledger_event_count},
            )
        ]

    def _warnings(
        self,
        source_ledger: SimuladoAppliedEventLedger,
        ready: bool,
    ) -> list[PropagationGuardrailWarning]:
        if not ready:
            return []
        return [
            PropagationGuardrailWarning(
                code="future_controlled_propagation_review_required",
                message="Future propagation still requires a later controlled propagation apply step.",
                related_artifact_type="simulado_applied_event_ledger",
                related_artifact_id=source_ledger.applied_event_ledger_id,
                metadata={},
            )
        ]
