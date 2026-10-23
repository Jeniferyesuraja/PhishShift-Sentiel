import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "site-packages" in path.parts:
            continue
        yield path


def test_no_live_url_fetch_imports():
    banned = {"requests", "urllib", "socket"}
    for path in _iter_python_files(ROOT / "src"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in banned:
                        raise AssertionError(f"Disallowed import in {path}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in banned:
                    raise AssertionError(f"Disallowed import in {path}: {node.module}")


def test_defanged_urls_only():
    from src.data.sanitize import is_defanged_url

    valid = [
        "hxxp://example[.]com/login",
        "hxxps://secure[.]co[.]uk/reset",
    ]
    invalid = [
        "http://example.com/login",
        "https://example.com",
        "example.com",
    ]
    for url in valid:
        assert is_defanged_url(url), url
    for url in invalid:
        assert not is_defanged_url(url), url
