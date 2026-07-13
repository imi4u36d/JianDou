from types import SimpleNamespace

from backend.services.workflow_auto_pilot_planner import WorkflowAutoPilotPlanner


def _version(stage_type: str, **overrides):  # noqa: ANN003, ANN202
    values = {
        "stage_type": stage_type,
        "stage_version_id": "version-1",
        "version_no": 1,
        "selected": 0,
        "clip_index": 0,
        "input_summary_json": "{}",
        "material_asset_id": "",
        "preview_url": "",
        "status": "FAILED",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_planner_selects_first_storyboard_before_loading_plan() -> None:
    workflow = SimpleNamespace(selected_storyboard_version_id="", final_join_asset_id="")
    versions = [
        _version("storyboard", stage_version_id="later", version_no=2),
        _version("storyboard", stage_version_id="first", version_no=1),
    ]

    steps = WorkflowAutoPilotPlanner().compute_next_steps(
        workflow,
        versions,
        lambda _version: (_ for _ in ()).throw(AssertionError("plan must not load before selection")),
    )

    assert steps == [{"type": "select_storyboard", "version_id": "first"}]


def test_planner_batches_missing_character_and_clip_keyframes() -> None:
    workflow = SimpleNamespace(selected_storyboard_version_id="storyboard-1", final_join_asset_id="")
    storyboard = _version(
        "storyboard",
        stage_version_id="storyboard-1",
        selected=1,
    )

    steps = WorkflowAutoPilotPlanner().compute_next_steps(
        workflow,
        [storyboard],
        lambda _version: ([{"name": "角色A"}], [{"clipIndex": 1}, {"clipIndex": 2}]),
    )

    assert steps == [
        {"type": "generate_keyframe", "clip_index": 1001},
        {"type": "generate_keyframe", "clip_index": 1},
        {"type": "generate_keyframe", "clip_index": 2},
    ]
