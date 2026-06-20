from core.paths import resolve_data_dir


def test_resolve_data_dir_in_flattened_docker_layout(tmp_path):
    app_dir = tmp_path / "app"
    docker_data = app_dir / "data"
    docker_data.mkdir(parents=True)

    assert resolve_data_dir(app_dir) == docker_data


def test_resolve_data_dir_in_repository_layout(tmp_path):
    pipeline_dir = tmp_path / "repo" / "pipeline"
    repo_data = tmp_path / "repo" / "data"
    pipeline_dir.mkdir(parents=True)
    repo_data.mkdir()

    assert resolve_data_dir(pipeline_dir) == repo_data
