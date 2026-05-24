from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from app.services.question_style_profiles import PSCPP_QUESTION_STYLE_PROFILE_ID


PSCPP_STUDY_CYCLE_PROFILE_ID = "marinha_dpc_pscpp_praticagem_study_cycle"


def _pscpp_study_cycle_profile_payload() -> dict[str, object]:
    return {
        "profile_id": PSCPP_STUDY_CYCLE_PROFILE_ID,
        "profile_name": "PSCPP Praticagem Study Cycle Guide",
        "exam_profile_id": PSCPP_QUESTION_STYLE_PROFILE_ID,
        "profile_type": "flexible_study_cycle_guidance",
        "guidance_mode": "editable_recommendation",
        "not_fixed_schedule": True,
        "user_override_allowed": True,
        "automatic_scheduler_mutation_allowed": False,
        "requires_current_edital_alignment": True,
        "profile_is_guidance_not_mandate": True,
        "historical_exam_evidence": {
            "exams": ["PSCPP/2011", "PSCPP/2012 Prova Rosa"],
            "use_as": "strategy_and_style_reference",
            "do_not_use_as_current_content_scope": True,
            "requires_current_edital_alignment": True,
        },
        "strategic_reading": [
            "PSCPP should be studied as technical decision-making in praticagem scenarios.",
            "It should not be treated as legislation-only or rote memorization.",
            "Study should integrate bibliography, COLREG, NORMAM, navigation, meteorology, shiphandling, manoeuvring, and operational scenarios.",
        ],
        "priority_blocks": [
            {
                "block_id": "manoeuvrability_shiphandling_tugs_restricted_waters",
                "priority": 1,
                "rationale": "core practical block; frequent in historical exams; expanded in current content",
                "includes": [
                    "manobrabilidade",
                    "aguas_rasas",
                    "canais",
                    "bank_effect",
                    "squat",
                    "interaction",
                    "rebocadores",
                    "atracacao",
                    "desatracacao",
                    "curva_de_giro",
                    "zig_zag",
                    "stopping",
                    "estabilidade_direcional",
                ],
            },
            {
                "block_id": "colreg_lights_marks_sound_signals",
                "priority": 2,
                "rationale": "situational rules and recurring exam block",
                "includes": [
                    "COLREG",
                    "canais_estreitos",
                    "visibilidade_restrita",
                    "luzes",
                    "marcas",
                    "sinais_sonoros",
                    "embarcacao_fundeada",
                    "sem_governo",
                    "restrita_por_calado",
                    "capacidade_de_manobra_restrita",
                ],
            },
            {
                "block_id": "restricted_navigation_radar_ecdis_tides_passage_planning",
                "priority": 3,
                "rationale": "operational navigation, instruments, radar, ECDIS, tides and passage planning",
                "includes": [
                    "rumos",
                    "marcacoes",
                    "agulhas",
                    "LDP",
                    "radar",
                    "ECDIS",
                    "AIS",
                    "GPS_DGPS",
                    "mare",
                    "passage_planning",
                    "pilot_on_board",
                    "bridge_team_management",
                ],
            },
            {
                "block_id": "arte_naval_foundations",
                "priority": 4,
                "rationale": "vocabulary and technical base for many statements",
                "includes": [
                    "nomenclatura",
                    "geometria",
                    "estabilidade",
                    "cabos",
                    "fundeio",
                    "aparelho_de_governo",
                    "deslocamento",
                    "calado",
                    "arqueacao",
                ],
            },
            {
                "block_id": "legislation_meteorology_communications_general_knowledge",
                "priority": 5,
                "rationale": "differentiating block; legal/normative and situational integration",
                "includes": [
                    "NORMAM",
                    "LESTA_RLESTA",
                    "Tribunal_Maritimo",
                    "IAFN",
                    "praticagem",
                    "meteorologia",
                    "oceanografia",
                    "METAREA",
                    "SMCP",
                    "GMDSS",
                    "CIS",
                    "PIANC",
                    "planejamento_portuario",
                ],
            },
        ],
        "phase_plan": [
            {
                "phase_id": "phase_1_base_technical_vocabulary",
                "suggested_period_label": "base tecnica e vocabulario",
                "objective": "build naval language and fundamentals",
                "focus": [
                    "Arte Naval basics",
                    "COLREG rules 1-19, lights, marks, sound signals",
                    "navigation basics: headings, bearings, compass, charts, LDP, radar basics",
                    "initial manoeuvrability: forces, rudder, propeller, turning circle, stopping",
                ],
                "output_products": [
                    "operational summaries",
                    "flashcards",
                    "confusion maps",
                    "basic questions",
                ],
            },
            {
                "phase_id": "phase_2_scenario_consolidation",
                "suggested_period_label": "consolidacao por cenarios",
                "objective": "stop studying by book only and start studying by operational problem",
                "scenario_examples": [
                    "narrow channel plus crossing barge",
                    "vessel constrained by draft approaching a bend",
                    "berthing with right-handed propeller and beam wind",
                    "two ships interacting in narrow channel",
                    "restricted visibility and radar use",
                    "tide window for manoeuvre",
                    "pilot on board and master/pilot exchange",
                    "anchoring with wind/current",
                    "collision/allision/flooding/grounding and Tribunal Maritimo competence",
                ],
                "output_products": [
                    "scenario notebook",
                    "case-based questions",
                    "decision trees",
                    "error notebook",
                ],
            },
            {
                "phase_id": "phase_3_deepening_and_new_question_production",
                "suggested_period_label": "aprofundamento e producao de questoes ineditas",
                "objective": "cover expanded content and produce probable-style questions",
                "focus": [
                    "hydrodynamic derivatives",
                    "dynamic stability",
                    "Nomoto",
                    "spiral curve",
                    "shallow waters",
                    "channels",
                    "interactions",
                    "IMO manoeuvrability standards",
                    "PIANC",
                    "modern tugs",
                    "pilot transfer",
                    "MPX",
                    "newer NORMAM/legislation references",
                    "applied meteorology/hydrometeorology",
                ],
                "question_generation_emphasis": [
                    "five-statement items",
                    "V/F sequence",
                    "operational scenario",
                    "applied calculation",
                    "normative cases",
                ],
            },
            {
                "phase_id": "phase_4_post_edital_alignment",
                "suggested_period_label": "pos-edital",
                "objective": "align to exact edital, indicated editions, and updated norms",
                "recommended_mix": {
                    "questions_and_simulados_percent": 60,
                    "active_review_percent": 25,
                    "directed_reading_weak_points_percent": 15,
                },
                "cadence_hints": [
                    "complete_simulado_every_2_weeks_until_september",
                    "weekly_complete_simulado_in_october",
                    "final_review_by_errors_maps_flashcards_in_november",
                ],
            },
        ],
        "weekly_distribution_hint_24h": {
            "total_hours": 24,
            "manoeuvrability_shiphandling_tugs": 6,
            "colreg_lights_marks_cis": 4,
            "restricted_navigation_radar_ecdis_tides": 4,
            "arte_naval": 3,
            "legislation_normam_tribunal_praticagem": 3,
            "meteorology_oceanography": 2,
            "communications_smcp_gmdss": 1,
            "cumulative_review_error_notebook": 1,
        },
        "time_scaling_rule": {
            "preserve_proportions_if_hours_change": True,
            "distribution_is_adaptive": True,
            "user_can_override_distribution": True,
        },
        "rotating_12_session_cycle": [
            {"session_number": 1, "theme": "Manoeuvrability: forces, resistance, propulsion"},
            {"session_number": 2, "theme": "COLREG: steering and sailing rules"},
            {"session_number": 3, "theme": "Arte Naval: nomenclature, geometry, stability"},
            {"session_number": 4, "theme": "Navigation: headings, bearings, compass, LDP"},
            {"session_number": 5, "theme": "Manoeuvrability: rudder, turning circle, zig-zag, stopping"},
            {"session_number": 6, "theme": "Legislation: NORMAM, LESTA/RLESTA, praticagem"},
            {"session_number": 7, "theme": "Shiphandling: berthing, unberthing, anchoring"},
            {"session_number": 8, "theme": "COLREG: lights, marks, sound signals"},
            {"session_number": 9, "theme": "Restricted navigation: radar, ECDIS, AIS, passage planning"},
            {"session_number": 10, "theme": "Tugs, interaction, bollard pull, escort"},
            {"session_number": 11, "theme": "Meteorology, oceanography, tides, METAREA"},
            {"session_number": 12, "theme": "Short simulado + error review"},
        ],
        "session_structure": {
            "active_review_minutes": 20,
            "directed_theory_minutes": "60_to_90",
            "questions_or_question_creation_minutes": 40,
            "error_notebook_flashcards_minutes": 20,
        },
        "question_training_progression": {
            "jan_mar_2027": "20 questions per week by topic",
            "apr_jun_2027": "40 questions per week plus own question creation",
            "jul_aug_2027": "1 partial simulado per week",
            "sep_2027": "1 complete simulado every 15 days",
            "oct_2027": "1 complete simulado per week",
            "nov_2027": "review by errors, not long reading",
            "guidance_only": True,
        },
        "study_products_per_topic": [
            "operational_summary",
            "trap_map",
            "flashcards",
            "original_questions",
        ],
        "notebook_system": [
            {
                "notebook_id": "concepts_the_banca_confuses",
                "examples": [
                    "estabilidade_direcional_vs_habilidade_de_giro",
                    "embarcacao_sem_governo_vs_capacidade_de_manobra_restrita",
                    "colisao_vs_abalroamento",
                    "fundeada_vs_amarrada_a_boia_vs_encalhada",
                    "raster_vs_vector",
                    "vento_verdadeiro_vs_aparente",
                    "corrente_vs_vento_na_manobra",
                    "advance_vs_transfer_vs_tactical_diameter",
                    "squat_vs_trim_dinamico_vs_sinkage",
                ],
            },
            {
                "notebook_id": "fatal_numbers_and_rules",
                "examples": [
                    "IMO manoeuvrability parameters",
                    "lights and marks",
                    "sound signals",
                    "tides",
                    "SOLAS equipment limits",
                    "GMDSS rules",
                    "squat/interaction proportions",
                    "Arte Naval coefficients/relations",
                ],
            },
            {
                "notebook_id": "scenario_notebook",
                "fields": [
                    "situation",
                    "applicable_rule",
                    "correct_conduct",
                    "likely_trap",
                    "possible_variation",
                ],
            },
        ],
        "question_generation_guidance": {
            "question_generation_profile_id": PSCPP_QUESTION_STYLE_PROFILE_ID,
            "use_pscpp_question_style_profile": True,
            "guiding_questions": [
                "what can the banca invert?",
                "which similar term can confuse?",
                "what exception exists?",
                "what is the real manoeuvre application?",
                "what number/proportion could be charged?",
                "which alternative would look right to someone who only memorized?",
            ],
            "prefer_source_grounded_questions": True,
            "prefer_scenario_rich_questions": True,
            "prefer_technically_plausible_distractors": True,
            "do_not_generate_answer_key_without_source_validation": True,
            "require_human_review_for_answer_key": True,
        },
        "integration_metadata": {
            "scheduler_mutation_disabled": True,
            "study_cycle_runtime_mutation_disabled": True,
            "question_style_profile_id": PSCPP_QUESTION_STYLE_PROFILE_ID,
            "use_pscpp_question_style_profile": True,
            "guidance_only": True,
        },
        "metadata": {
            "llm_used": False,
            "external_calls_used": False,
            "runtime_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "calendar_mutation_performed": False,
            "profile_scope": "study_cycle_guidance_only",
        },
    }


def get_pscpp_study_cycle_profile() -> dict[str, object]:
    return deepcopy(_pscpp_study_cycle_profile_payload())


def get_study_cycle_profile(profile_id: str | None) -> dict[str, object] | None:
    if profile_id != PSCPP_STUDY_CYCLE_PROFILE_ID:
        return None
    return get_pscpp_study_cycle_profile()


def _scale_distribution(distribution: Mapping[str, object], *, total_hours: float) -> dict[str, object]:
    base_total = float(distribution.get("total_hours", 0) or 0)
    if base_total <= 0:
        return {"total_hours": total_hours}
    ratio = round(float(total_hours) / base_total, 4)
    scaled: dict[str, object] = {"total_hours": float(total_hours), "scaling_ratio": ratio}
    for key, value in distribution.items():
        if key == "total_hours":
            continue
        if isinstance(value, (int, float)):
            scaled[key] = round(float(value) * ratio, 2)
    return scaled


def build_study_cycle_guidance_metadata(
    profile_id: str | None,
    *,
    weekly_hours: float = 24,
    base_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    metadata = dict(base_metadata or {})
    profile = get_study_cycle_profile(profile_id)
    if profile is None:
        return metadata

    weekly_distribution = profile["weekly_distribution_hint_24h"]
    metadata.update(
        {
            "study_cycle_profile_id": profile["profile_id"],
            "study_cycle_profile_name": profile["profile_name"],
            "exam_profile_id": profile["exam_profile_id"],
            "profile_type": profile["profile_type"],
            "guidance_mode": profile["guidance_mode"],
            "not_fixed_schedule": profile["not_fixed_schedule"],
            "user_override_allowed": profile["user_override_allowed"],
            "automatic_scheduler_mutation_allowed": profile["automatic_scheduler_mutation_allowed"],
            "requires_current_edital_alignment": profile["requires_current_edital_alignment"],
            "profile_is_guidance_not_mandate": profile["profile_is_guidance_not_mandate"],
            "historical_exam_evidence": deepcopy(profile["historical_exam_evidence"]),
            "priority_blocks": deepcopy(profile["priority_blocks"]),
            "phase_plan": deepcopy(profile["phase_plan"]),
            "weekly_distribution_hint_24h": deepcopy(weekly_distribution),
            "scaled_weekly_distribution": _scale_distribution(weekly_distribution, total_hours=weekly_hours),
            "time_scaling_rule": deepcopy(profile["time_scaling_rule"]),
            "rotating_12_session_cycle": deepcopy(profile["rotating_12_session_cycle"]),
            "session_structure": deepcopy(profile["session_structure"]),
            "question_training_progression": deepcopy(profile["question_training_progression"]),
            "study_products_per_topic": list(profile["study_products_per_topic"]),
            "notebook_system": deepcopy(profile["notebook_system"]),
            "question_generation_guidance": deepcopy(profile["question_generation_guidance"]),
            "integration_metadata": deepcopy(profile["integration_metadata"]),
        }
    )
    return metadata


def enrich_study_cycle_blueprint_with_profile(
    *,
    profile_id: str | None,
    blueprint_metadata: Mapping[str, object] | None = None,
    weekly_hours: float = 24,
) -> dict[str, object]:
    return build_study_cycle_guidance_metadata(
        profile_id,
        weekly_hours=weekly_hours,
        base_metadata=blueprint_metadata,
    )
