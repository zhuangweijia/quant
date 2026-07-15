import tomllib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_market_data_dependency_is_installed_by_default():
    pyproject = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text())
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.startswith("akshare") for dependency in dependencies)


def test_dockerfile_does_not_reference_an_undefined_extra():
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()

    assert ".[all-market]" not in dockerfile
