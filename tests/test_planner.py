"""
Tests for Task Planner
"""

import pytest
from agent.planner import TaskPlanner, TaskPlan, TaskStep, planner


@pytest.fixture
def fresh_planner():
    """Create a fresh planner instance."""
    return TaskPlanner()


def test_create_plan(fresh_planner):
    """Test creating a task plan."""
    plan = fresh_planner.create_plan(
        session_id="test-session",
        goal="Research AI trends",
        steps=[
            {"description": "Search for latest AI news", "tool": "web_search"},
            {"description": "Analyze top articles", "tool": "web_scrape"},
            {"description": "Write summary report", "tool": "file_write"}
        ]
    )

    assert plan.goal == "Research AI trends"
    assert len(plan.steps) == 3
    assert plan.steps[0].description == "Search for latest AI news"
    assert plan.steps[0].tool == "web_search"
    assert plan.steps[0].status == "pending"


def test_get_plan(fresh_planner):
    """Test retrieving a plan."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test goal",
        steps=[{"description": "Step 1"}]
    )

    plan = fresh_planner.get_plan("test-session")
    assert plan is not None
    assert plan.goal == "Test goal"


def test_get_plan_nonexistent(fresh_planner):
    """Test retrieving non-existent plan."""
    plan = fresh_planner.get_plan("nonexistent")
    assert plan is None


def test_mark_step_done(fresh_planner):
    """Test marking a step as done."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[
            {"description": "Step 1"},
            {"description": "Step 2"}
        ]
    )

    fresh_planner.mark_step_done("test-session", 1, "Completed successfully")

    plan = fresh_planner.get_plan("test-session")
    assert plan.steps[0].status == "done"
    assert plan.steps[0].result == "Completed successfully"
    assert plan.current_step == 1


def test_mark_step_failed(fresh_planner):
    """Test marking a step as failed."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[{"description": "Step 1"}]
    )

    fresh_planner.mark_step_failed("test-session", 1, "API error")

    plan = fresh_planner.get_plan("test-session")
    assert plan.steps[0].status == "failed"
    assert plan.steps[0].result == "API error"


def test_mark_step_in_progress(fresh_planner):
    """Test marking a step as in progress."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[{"description": "Step 1"}]
    )

    fresh_planner.mark_step_in_progress("test-session", 1)

    plan = fresh_planner.get_plan("test-session")
    assert plan.steps[0].status == "in_progress"


def test_plan_is_complete(fresh_planner):
    """Test plan completion check."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[
            {"description": "Step 1"},
            {"description": "Step 2"}
        ]
    )

    plan = fresh_planner.get_plan("test-session")
    assert not plan.is_complete

    fresh_planner.mark_step_done("test-session", 1)
    fresh_planner.mark_step_done("test-session", 2)

    assert plan.is_complete


def test_plan_progress(fresh_planner):
    """Test plan progress tracking."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[
            {"description": "Step 1"},
            {"description": "Step 2"},
            {"description": "Step 3"}
        ]
    )

    plan = fresh_planner.get_plan("test-session")
    assert plan.progress == "0/3"

    fresh_planner.mark_step_done("test-session", 1)
    assert plan.progress == "1/3"


def test_plan_to_context(fresh_planner):
    """Test plan context generation."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Research AI",
        steps=[
            {"description": "Search web", "tool": "web_search"},
            {"description": "Write report"}
        ]
    )

    plan = fresh_planner.get_plan("test-session")
    context = plan.to_context()

    assert "Research AI" in context
    assert "Search web" in context
    assert "web_search" in context
    assert "Write report" in context


def test_clear_plan(fresh_planner):
    """Test clearing a plan."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[{"description": "Step 1"}]
    )

    fresh_planner.clear_plan("test-session")
    assert fresh_planner.get_plan("test-session") is None


def test_plan_current_step(fresh_planner):
    """Test current step tracking."""
    fresh_planner.create_plan(
        session_id="test-session",
        goal="Test",
        steps=[
            {"description": "Step 1"},
            {"description": "Step 2"}
        ]
    )

    plan = fresh_planner.get_plan("test-session")
    assert plan.current.description == "Step 1"

    fresh_planner.mark_step_done("test-session", 1)
    assert plan.current.description == "Step 2"