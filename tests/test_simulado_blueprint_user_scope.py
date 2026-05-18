from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from tests.test_simulado_blueprint_foundation import persist_graph_fixture
from tests.fixtures.study_cycle_graphs import balanced_cycle_fixture


def test_user_scope_blocks_cross_user_simulado_blueprint_build_and_reads(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    graph = persist_graph_fixture(repository, balanced_cycle_fixture(), user_id="user-a")
    cycle_service = StudyCycleOrchestratorService(repository)
    cycle_state = cycle_service.build_cycle(graph.graph_id, user_id="user-a")
    builder = SimuladoBlueprintBuilderService(repository)

    denied = builder.build_blueprint(cycle_state.cycle_id, user_id="user-b", profile_id="exam-profile:fgv")
    allowed = builder.build_blueprint(cycle_state.cycle_id, user_id="user-a", profile_id="exam-profile:fgv")

    assert denied is not None
    assert denied.status == "insufficient_cycle"
    assert allowed.status == "ready_for_review"
    assert repository.get_simulado_blueprint(cycle_state.cycle_id, user_id="user-b") is None
    assert repository.get_simulado_blueprint(cycle_state.cycle_id, user_id="user-a") is not None
    assert repository.get_simulado_blueprint_by_id(f"simulado:{cycle_state.cycle_id}:exam-profile:fgv", user_id="user-b") is None
    assert repository.get_simulado_blueprint_by_id(f"simulado:{cycle_state.cycle_id}:exam-profile:fgv", user_id="user-a") is not None
