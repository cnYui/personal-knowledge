from app.services.history_query_planner import HistoryQueryPlanner


def test_planner_uses_current_only_for_present_state_question():
    planner = HistoryQueryPlanner()

    plan = planner.plan('OpenAI 现在和 Microsoft 是什么关系？')

    assert plan.steps == ['current_retrieval']


def test_planner_uses_history_only_for_pure_history_question():
    planner = HistoryQueryPlanner()

    plan = planner.plan('OpenAI 和 Microsoft 以前的关系如何变化？')

    assert plan.steps == ['history_retrieval']


def test_planner_uses_dual_tool_flow_for_current_vs_history_question():
    planner = HistoryQueryPlanner()

    plan = planner.plan('OpenAI 和 Microsoft 当前关系与历史转折点有什么差异？')

    assert plan.steps == ['current_retrieval', 'history_retrieval', 'compose_answer']
