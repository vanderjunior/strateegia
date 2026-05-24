from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence


PSCPP_QUESTION_STYLE_PROFILE_ID = "marinha_dpc_pscpp_praticagem"
PSCPP_EXAM_PROFILE_ID = "exam-profile:marinha-pscpp"


def _pscpp_question_style_profile_payload() -> dict[str, object]:
    return {
        "profile_id": PSCPP_QUESTION_STYLE_PROFILE_ID,
        "profile_name": "Marinha/DPC PSCPP Praticagem",
        "format": "multiple_choice",
        "options": {
            "options_count": 5,
            "answer_labels": ["a", "b", "c", "d", "e"],
        },
        "source_grounding": {
            "source_required": True,
            "bibliography_anchor_required": True,
            "question_without_source_should_be_blocked": True,
            "source_title_should_be_visible_in_blueprint": True,
            "source_title_in_stem_preferred": True,
            "edition_reference_allowed": True,
            "current_edital_alignment_required": True,
        },
        "historical_exam_evidence": {
            "exam": "PSCPP/2012 Prova Rosa",
            "use_as": "style_and_archetype_reference",
            "do_not_use_as_current_content_scope": True,
            "requires_current_edital_alignment": True,
        },
        "bibliography_behavior": {
            "explicit_source_citation_common": True,
            "source_title_in_stem_common": True,
            "edition_year_often_present": True,
            "technical_english_sources_common": True,
            "normative_sources_common": True,
        },
        "question_archetypes": [
            {
                "archetype_id": "statement_combination",
                "statement_count_min": 4,
                "statement_count_max": 5,
                "options_type": "combination_of_true_statements",
                "requires_statement_truth_table": True,
                "source_support_per_statement_required": True,
            },
            {
                "archetype_id": "true_false_sequence_multiple_choice",
                "statement_count_min": 4,
                "statement_count_max": 5,
                "options_type": "vf_sequence",
                "answer_format": "sequence_option",
                "source_support_per_statement_required": True,
            },
            {
                "archetype_id": "incorrect_alternative",
                "command": "assinale a opcao incorreta",
                "trap_risk": "high",
                "requires_negative_command_warning": True,
            },
            {
                "archetype_id": "applied_calculation",
                "requires_numeric_reasoning": True,
                "requires_units": True,
                "requires_step_validation": True,
                "answer_options_are_numeric_or_operational": True,
                "do_not_generate_numeric_answer_without_explicit_source_or_formula": True,
            },
            {
                "archetype_id": "technical_operational_scenario",
                "scenario_required": True,
                "role_context": ["pratico", "comandante", "oficial_de_quarto"],
                "operational_decision_required": True,
            },
            {
                "archetype_id": "technical_gap_fill_multiple_choice",
                "requires_exact_bibliographic_value": True,
                "high_source_dependency": True,
            },
            {
                "archetype_id": "normative_case_application",
                "source_support_required": True,
                "normative_reference_required": True,
            },
        ],
        "style_traits": {
            "technical_density": "very_high",
            "scenario_context": "frequent",
            "bibliographic_literalness": "high",
            "operational_reasoning": "high",
            "calculation_presence": "moderate",
            "english_technical_terms": "frequent",
            "negative_commands": "present",
            "multi_statement_items": "frequent",
        },
        "distractor_policy": {
            "must_be_technically_plausible": True,
            "common_confusions": [
                "BE_vs_BB",
                "proa_vs_popa",
                "vento_vs_corrente",
                "aguas_rasas_vs_aguas_profundas",
                "squat_vs_bank_effect",
                "direct_towing_vs_indirect_towing",
                "regra_COLREG_vs_excecao",
                "rumo_verdadeiro_vs_rumo_magnetico_vs_rumo_da_agulha",
            ],
        },
        "scoring_behavior": {
            "uniform_weight": False,
            "observed_weights": [0.8, 1.0, 1.2, 1.3, 1.6, 2.0],
            "weight_should_come_from_edital_or_blueprint": True,
            "do_not_assume_default_weight": True,
        },
        "topic_distribution_hints": [
            "arte_naval_construcao_naval",
            "shiphandling_manobra",
            "colreg_cis_luzes_marcas_regras",
            "navegacao_costeira_mare_instrumentos_ecdis_avisos",
            "rebocadores",
            "normam_legislacao_maritima_autoridade_maritima_iafn",
            "meteorologia_embarque_pratico_correntes_locais",
            "arquitetura_naval_hidrodinamica_resistencia_cavitacao_giro_squat_interacao",
        ],
        "bibliography_examples": [
            "Arte Naval - Maurilio M. Fonseca",
            "Shiphandling for the Mariner - MacElrevey",
            "COLREG",
            "CIS",
            "NORMAM-12/DPC",
            "NORMAM-08/DPC",
            "NORMAM-09/DPC",
            "Lei 2.180/1954",
            "Portaria no 156/MB",
            "Navegacao: A Ciencia e a Arte - Altineu Pires Miguens",
            "Bridge Team Management",
            "ECDIS / Resolucao IMO A.817(19)",
            "Rebocadores Portuarios - CONAPRA",
            "Tug Use in Port - Henk Hensen",
            "Principles of Naval Architecture - SNAME",
            "Squat Interaction Manoeuvring - The Nautical Institute",
            "Naval Shiphandling - Crenshaw",
            "Meteorologia e Oceanografia - Lobo e Soares",
            "Roteiro Costa Norte",
            "Tabuas das Mares",
        ],
        "safety_rules": {
            "do_not_generate_without_source": True,
            "do_not_generate_numeric_answer_without_explicit_source_or_formula": True,
            "mark_negative_command_questions": True,
            "require_human_review_for_answer_key": True,
            "require_source_support_per_statement": True,
            "final_answer_key_should_not_be_generated_without_source_validation": True,
        },
        "templates": [
            {
                "template_id": "bibliography_statements",
                "template_label": "Bibliography + statements",
                "template_text": (
                    'De acordo com o contido no livro "{fonte}", analise as afirmativas abaixo, '
                    "identifique as verdadeiras e assinale a opcao correta: ..."
                ),
            },
            {
                "template_id": "operational_scenario",
                "template_label": "Operational scenario",
                "template_text": (
                    "O Pratico {nome} esta assessorando a manobra de {operacao} de um navio {tipo}, "
                    "em condicoes de {vento/corrente/visibilidade/profundidade}. "
                    "Considerando {fonte/regra}, e correto afirmar que:"
                ),
            },
            {
                "template_id": "applied_calculation",
                "template_label": "Applied calculation",
                "template_text": "Considerando os dados abaixo, calcule/assinale: ...",
            },
            {
                "template_id": "incorrect_alternative",
                "template_label": "Incorrect alternative",
                "template_text": "De acordo com {fonte}, assinale a opcao INCORRETA:",
            },
            {
                "template_id": "technical_gap_fill",
                "template_label": "Technical gap fill",
                "template_text": (
                    "De acordo com {fonte}, o fenomeno {X} aumenta/diminui de ______ a ______. "
                    "Assinale a opcao que completa corretamente as lacunas."
                ),
            },
        ],
        "applicable_generation_flows": ["simulado", "fixation", "review", "summary_reading"],
        "metadata": {
            "profile_scope": "question_style_profile_only",
            "runtime_behavior_modified": False,
            "llm_used": False,
            "external_calls_used": False,
        },
    }


def resolve_question_style_profile_id(profile_id: str | None) -> str | None:
    if profile_id in {PSCPP_QUESTION_STYLE_PROFILE_ID, PSCPP_EXAM_PROFILE_ID}:
        return PSCPP_QUESTION_STYLE_PROFILE_ID
    return None


def get_pscpp_question_style_profile() -> dict[str, object]:
    return deepcopy(_pscpp_question_style_profile_payload())


def get_question_style_profile(profile_id: str | None) -> dict[str, object] | None:
    resolved = resolve_question_style_profile_id(profile_id)
    if resolved != PSCPP_QUESTION_STYLE_PROFILE_ID:
        return None
    return get_pscpp_question_style_profile()


def get_allowed_archetypes_for_profile(profile_id: str | None) -> list[str]:
    profile = get_question_style_profile(profile_id)
    if profile is None:
        return []
    return [
        str(item["archetype_id"])
        for item in profile["question_archetypes"]
        if isinstance(item, dict) and "archetype_id" in item
    ]


def get_profile_template_hints(profile_id: str | None) -> list[dict[str, str]]:
    profile = get_question_style_profile(profile_id)
    if profile is None:
        return []
    return [
        {
            "template_id": str(item["template_id"]),
            "template_label": str(item["template_label"]),
        }
        for item in profile["templates"]
        if isinstance(item, dict)
    ]


def select_default_archetype_for_context(
    profile_id: str | None,
    *,
    delivery_context: str,
) -> str | None:
    if resolve_question_style_profile_id(profile_id) != PSCPP_QUESTION_STYLE_PROFILE_ID:
        return None
    defaults = {
        "simulado": "technical_operational_scenario",
        "fixation": "statement_combination",
        "review": "true_false_sequence_multiple_choice",
        "summary_reading": "incorrect_alternative",
    }
    return defaults.get(delivery_context, "technical_operational_scenario")


def build_question_style_validation(
    *,
    exam_profile_id: str | None,
    requested_archetype: str | None,
    source_present: bool,
    formula_supported: bool,
    per_statement_source_support: bool,
    negative_command: bool,
    bibliography_anchor_present: bool | None = None,
    source_title_visible: bool | None = None,
    current_edital_alignment_present: bool | None = None,
    exact_source_value_present: bool = False,
    scenario_present: bool = False,
    normative_source_present: bool = False,
    units_present: bool = False,
    delivery_context: str = "simulado",
) -> dict[str, object]:
    if resolve_question_style_profile_id(exam_profile_id) != PSCPP_QUESTION_STYLE_PROFILE_ID:
        return {}

    allowed_archetypes = get_allowed_archetypes_for_profile(exam_profile_id)
    default_archetype = select_default_archetype_for_context(
        exam_profile_id,
        delivery_context=delivery_context,
    )
    selected_archetype = requested_archetype or default_archetype
    blockers: list[str] = []
    warnings: list[str] = []
    state = "style_profile_ready"
    invalid_requested_archetype = False

    if requested_archetype and requested_archetype not in allowed_archetypes:
        invalid_requested_archetype = True
        warnings.append("invalid_pscpp_archetype_requested")
        selected_archetype = default_archetype
        state = "needs_review"

    bibliography_anchor_present = source_present if bibliography_anchor_present is None else bibliography_anchor_present
    source_title_visible = bibliography_anchor_present if source_title_visible is None else source_title_visible
    current_edital_alignment_present = (
        source_present if current_edital_alignment_present is None else current_edital_alignment_present
    )

    if not source_present:
        blockers.append("blocked_by_missing_source")
        state = "blocked_by_missing_source"

    if not bibliography_anchor_present:
        warnings.append("bibliography_anchor_missing")
        if not blockers:
            state = "needs_review"

    if not source_title_visible:
        warnings.append("source_title_visibility_missing")
        if not blockers:
            state = "needs_review"

    if not current_edital_alignment_present:
        warnings.append("current_edital_alignment_missing")
        if not blockers:
            state = "needs_review"

    if selected_archetype == "applied_calculation":
        if not formula_supported:
            warnings.append("numeric_source_or_formula_validation_required")
            if not blockers:
                state = "needs_review"
        if not units_present:
            warnings.append("calculation_units_required")
            if not blockers:
                state = "needs_review"

    if selected_archetype in {
        "statement_combination",
        "true_false_sequence_multiple_choice",
    } and not per_statement_source_support:
        warnings.append("source_support_per_statement_required")
        if not blockers:
            state = "needs_review"

    if selected_archetype == "technical_gap_fill_multiple_choice" and not exact_source_value_present:
        warnings.append("exact_source_value_required")
        if not blockers:
            state = "needs_review"

    if selected_archetype == "technical_operational_scenario" and not scenario_present:
        warnings.append("technical_operational_scenario_context_required")
        if not blockers:
            state = "needs_review"

    if selected_archetype == "normative_case_application" and not normative_source_present:
        warnings.append("normative_reference_required")
        if not blockers:
            state = "needs_review"

    if negative_command or selected_archetype == "incorrect_alternative":
        warnings.append("negative_command_review_marker_required")
        if not blockers and state == "style_profile_ready":
            state = "needs_review"

    source_grounding_state = "ready" if source_present else "blocked"
    bibliography_anchor_state = "ready" if bibliography_anchor_present else "needs_review"
    source_title_visibility_state = "ready" if source_title_visible else "needs_review"
    current_edital_alignment_state = "ready" if current_edital_alignment_present else "needs_review"

    if selected_archetype == "applied_calculation" and not formula_supported:
        source_grounding_state = "needs_review"
    if selected_archetype in {"statement_combination", "true_false_sequence_multiple_choice"} and not per_statement_source_support:
        source_grounding_state = "needs_review"
    if selected_archetype == "technical_gap_fill_multiple_choice" and not exact_source_value_present:
        source_grounding_state = "needs_review"

    archetype_requirements = {}
    if selected_archetype == "statement_combination":
        archetype_requirements = {
            "statement_count_min": 4,
            "statement_count_max": 5,
            "source_support_per_statement_required": True,
        }
    elif selected_archetype == "true_false_sequence_multiple_choice":
        archetype_requirements = {
            "statement_count_min": 4,
            "statement_count_max": 5,
            "answer_format": "sequence_option",
            "source_support_per_statement_required": True,
        }
    elif selected_archetype == "incorrect_alternative":
        archetype_requirements = {
            "negative_command": True,
            "trap_risk": "high",
        }
    elif selected_archetype == "applied_calculation":
        archetype_requirements = {
            "requires_numeric_reasoning": True,
            "requires_units": True,
            "requires_formula_or_explicit_source": True,
        }
    elif selected_archetype == "technical_operational_scenario":
        archetype_requirements = {
            "scenario_required": True,
            "role_context": ["pratico", "comandante", "oficial_de_quarto"],
        }
    elif selected_archetype == "technical_gap_fill_multiple_choice":
        archetype_requirements = {
            "requires_exact_source_value": True,
        }
    elif selected_archetype == "normative_case_application":
        archetype_requirements = {
            "normative_reference_required": True,
        }

    return {
        "state": state,
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
        "requested_archetype": requested_archetype,
        "selected_archetype": selected_archetype,
        "recommended_archetype": default_archetype,
        "allowed_archetypes": allowed_archetypes,
        "invalid_requested_archetype": invalid_requested_archetype,
        "archetype_requirements": archetype_requirements,
        "source_grounding_state": source_grounding_state,
        "bibliography_anchor_state": bibliography_anchor_state,
        "source_title_visibility_state": source_title_visibility_state,
        "current_edital_alignment_state": current_edital_alignment_state,
        "source_required": True,
        "bibliography_anchor_required": True,
        "requires_human_review_for_answer_key": True,
        "requires_current_edital_alignment": True,
    }


def enrich_question_generation_blueprint_with_style_profile(
    *,
    exam_profile_id: str | None,
    blueprint_metadata: Mapping[str, object] | None = None,
    source_titles: Sequence[str] | None = None,
    source_present: bool,
    requested_archetype: str | None = None,
    formula_supported: bool = False,
    per_statement_source_support: bool = False,
    negative_command: bool = False,
    bibliography_anchor_present: bool | None = None,
    source_title_visible: bool | None = None,
    current_edital_alignment_present: bool | None = None,
    exact_source_value_present: bool = False,
    scenario_present: bool = False,
    normative_source_present: bool = False,
    units_present: bool = False,
    delivery_context: str = "simulado",
) -> dict[str, object]:
    metadata = dict(blueprint_metadata or {})
    profile = get_question_style_profile(exam_profile_id)
    if profile is None:
        return metadata

    unique_source_titles = sorted(
        {
            str(title).strip()
            for title in (source_titles or [])
            if isinstance(title, str) and title.strip()
        }
    )[:5]
    validation = build_question_style_validation(
        exam_profile_id=exam_profile_id,
        requested_archetype=requested_archetype,
        source_present=source_present,
        formula_supported=formula_supported,
        per_statement_source_support=per_statement_source_support,
        negative_command=negative_command,
        bibliography_anchor_present=bibliography_anchor_present,
        source_title_visible=source_title_visible,
        current_edital_alignment_present=current_edital_alignment_present,
        exact_source_value_present=exact_source_value_present,
        scenario_present=scenario_present,
        normative_source_present=normative_source_present,
        units_present=units_present,
        delivery_context=delivery_context,
    )
    archetypes = get_allowed_archetypes_for_profile(exam_profile_id)
    templates = get_profile_template_hints(exam_profile_id)
    resolved_exam_profile_id = resolve_question_style_profile_id(exam_profile_id)

    metadata.update(
        {
            "exam_profile_id": resolved_exam_profile_id,
            "question_style_profile_id": profile["profile_id"],
            "question_style_profile_name": profile["profile_name"],
            "format": profile["format"],
            "options_count": profile["options"]["options_count"],
            "answer_labels": list(profile["options"]["answer_labels"]),
            "source_required": True,
            "bibliography_anchor_required": True,
            "source_title_should_be_visible_in_blueprint": True,
            "source_title_in_stem_preferred": True,
            "edition_reference_allowed": True,
            "current_edital_alignment_required": True,
            "allowed_archetypes": archetypes,
            "preferred_templates": templates,
            "distractor_policy": deepcopy(profile["distractor_policy"]),
            "scoring_behavior": deepcopy(profile["scoring_behavior"]),
            "safety_rules": deepcopy(profile["safety_rules"]),
            "human_review_required_for_answer_key": True,
            "historical_exam_evidence": deepcopy(profile["historical_exam_evidence"]),
            "style_traits": deepcopy(profile["style_traits"]),
            "applicable_generation_flows": list(profile["applicable_generation_flows"]),
            "delivery_context": delivery_context,
            "requested_question_archetype": requested_archetype,
            "selected_question_archetype": validation.get("selected_archetype"),
            "recommended_question_archetype": validation.get("recommended_archetype"),
            "visible_source_titles": unique_source_titles,
            "source_grounding_validation_state": validation.get("source_grounding_state"),
            "bibliography_anchor_validation_state": validation.get("bibliography_anchor_state"),
            "source_title_visibility_validation_state": validation.get("source_title_visibility_state"),
            "current_edital_alignment_validation_state": validation.get("current_edital_alignment_state"),
            "question_style_validation": validation,
        }
    )
    return metadata
