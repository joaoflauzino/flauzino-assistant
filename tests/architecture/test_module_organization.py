"""Architecture gate for ``python-modular-code-organization`` (policy as code).

Checks the production packages of every API against five measurable rules:

* **A** — a flat directory whose modules share a domain prefix (≥ 5 files or ≥ 800 LOC)
  must be promoted to a flat domain package (skill rule 8).
* **B** — no production module may exceed the file size ceiling (skill rule 6).
* **C** — no package may be named after a Python keyword (skill rule 8.3).
* **D** — no module may repeat the name of the package it lives in (skill rule 8.2).
* **E** — internal ``__init__.py`` files must not declare ``__all__`` (skill rule 5).

Debt frozen on 2026-11-02 lives in ``BASELINE``: every entry names the phase that pays
it down. New violations fail the suite; the allowlist is deleted in phase 6.6.
"""

import keyword
import pathlib
from collections import defaultdict
from collections.abc import Iterable, Sequence

API_ROOTS = ("finance_api", "agent_api", "telegram_api", "graph_api")
SKIPPED_DIRECTORIES = {"tests", "__pycache__", ".pytest_cache"}
MAX_FILE_LOC = 300
MAX_CLUSTER_FILES = 5
MAX_CLUSTER_LOC = 800
RULE_LEGEND = (
    "A=cluster de prefixo (>=5 arqs ou >=800 LOC) vira pacote plano; "
    "B=arquivo acima de 300 LOC; C=pacote com nome de keyword; "
    "D=modulo repetindo o nome do pacote; E=__all__ em __init__ interno."
)

BASELINE: dict[str, str] = {
    "D|graph_api/services/graph_service.py": "6.5 — renomear para graph.py",
    "D|telegram_api/handlers/balance_handler.py": "6.5 — renomear para balance.py",
    "D|telegram_api/handlers/balance_summary_handler.py": "6.5 — renomear",
    "D|telegram_api/handlers/command_handler.py": "6.5 — renomear para command.py",
    "D|telegram_api/handlers/expense_handler.py": "6.5 — renomear para expense.py",
    "D|telegram_api/handlers/income_handler.py": "6.5 — renomear para income.py",
    "D|telegram_api/handlers/message_handler.py": "6.5 — renomear para message.py",
    "D|telegram_api/handlers/photo_handler.py": "6.5 — renomear para photo.py",
    "D|telegram_api/handlers/voice_handler.py": "6.5 — renomear para voice.py",
    "D|telegram_api/services/session_service.py": "6.5 — renomear para session.py",
}


def iter_production_files(roots: Sequence[pathlib.Path]) -> Iterable[pathlib.Path]:
    """Yields production modules, skipping tests and caches."""
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if SKIPPED_DIRECTORIES & set(path.parts):
                continue
            yield path


def count_loc(path: pathlib.Path) -> int:
    """Counts the physical lines of a module."""
    return len(path.read_text(encoding="utf-8").splitlines())


def collect_cluster_violations(paths: Sequence[pathlib.Path]) -> dict[str, str]:
    """Rule A: detects prefix groups that behave like an uncreated package."""
    groups: dict[tuple[pathlib.Path, str], list[pathlib.Path]] = defaultdict(list)
    for path in paths:
        if path.name == "__init__.py":
            continue
        groups[(path.parent, path.stem.split("_")[0])].append(path)

    violations: dict[str, str] = {}
    for (directory, prefix), files in groups.items():
        loc = sum(count_loc(path) for path in files)
        if len(files) >= MAX_CLUSTER_FILES or loc >= MAX_CLUSTER_LOC:
            violations[f"A|{directory.as_posix()}|{prefix}"] = (
                f"{len(files)} módulos / {loc} LOC compartilham o prefixo '{prefix}_'"
            )
    return violations


def collect_size_violations(paths: Sequence[pathlib.Path]) -> dict[str, str]:
    """Rule B: detects modules above the size ceiling."""
    violations: dict[str, str] = {}
    for path in paths:
        loc = count_loc(path)
        if loc > MAX_FILE_LOC:
            violations[f"B|{path.as_posix()}"] = f"{loc} LOC (> {MAX_FILE_LOC})"
    return violations


def collect_keyword_package_violations(roots: Sequence[pathlib.Path]) -> dict[str, str]:
    """Rule C: detects packages named after Python keywords."""
    violations: dict[str, str] = {}
    for root in roots:
        for directory in sorted(root.rglob("*")):
            if not directory.is_dir() or SKIPPED_DIRECTORIES & set(directory.parts):
                continue
            if keyword.iskeyword(directory.name) or keyword.issoftkeyword(directory.name):
                violations[f"C|{directory.as_posix()}"] = (
                    f"pacote '{directory.name}' é palavra reservada do Python"
                )
    return violations


def collect_package_repetition_violations(paths: Sequence[pathlib.Path]) -> dict[str, str]:
    """Rule D: detects modules that repeat the name of their package."""
    violations: dict[str, str] = {}
    for path in paths:
        if path.name == "__init__.py":
            continue
        package = path.parent.name
        singular = package.rstrip("s")
        stem = path.stem
        repeats = stem == package or stem.startswith(f"{package}_") or stem.endswith(f"_{singular}")
        if repeats:
            violations[f"D|{path.as_posix()}"] = f"nome do módulo repete o pacote '{package}'"
    return violations


def collect_package_surface_violations(paths: Sequence[pathlib.Path]) -> dict[str, str]:
    """Rule E: detects ``__all__`` declarations in internal ``__init__`` modules."""
    violations: dict[str, str] = {}
    for path in paths:
        if path.name != "__init__.py" or path.parent.name in API_ROOTS:
            continue
        if "__all__" in path.read_text(encoding="utf-8"):
            violations[f"E|{path.as_posix()}"] = "«__all__» em módulo interno (Regra 5)"
    return violations


def collect_violations(roots: Sequence[pathlib.Path] | None = None) -> dict[str, str]:
    """Collects every rule violation for the given roots (defaults to all APIs)."""
    resolved_roots = tuple(pathlib.Path(root) for root in (roots or API_ROOTS))
    paths = list(iter_production_files(resolved_roots))

    violations: dict[str, str] = {}
    violations |= collect_cluster_violations(paths)
    violations |= collect_size_violations(paths)
    violations |= collect_keyword_package_violations(resolved_roots)
    violations |= collect_package_repetition_violations(paths)
    violations |= collect_package_surface_violations(paths)
    return violations


def format_report(violations: dict[str, str]) -> str:
    """Renders an actionable failure message for the gate."""
    lines = [
        "Novas violações de organização de módulos:",
        *(f"  [{key}] {detail}" for key, detail in sorted(violations.items())),
        "",
        RULE_LEGEND,
        "Conserte ou registre a dívida em BASELINE com a fase que a quita (spec 6.1).",
    ]
    return "\n".join(lines)


def write_module(path: pathlib.Path, content: str = "") -> pathlib.Path:
    """Creates a module (and parents) for the synthetic rule tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_no_new_module_organization_violations() -> None:
    new_violations = {
        key: detail for key, detail in collect_violations().items() if key not in BASELINE
    }

    assert not new_violations, format_report(new_violations)


def test_cluster_rule_flags_a_prefix_group_over_the_threshold(tmp_path: pathlib.Path) -> None:
    for name in ("import_a", "import_b", "import_c", "import_d", "import_e"):
        write_module(tmp_path / "services" / f"{name}.py")

    violations = collect_violations([tmp_path])

    assert f"A|{(tmp_path / 'services').as_posix()}|import" in violations


def test_cluster_rule_ignores_groups_below_the_threshold(tmp_path: pathlib.Path) -> None:
    write_module(tmp_path / "services" / "payment_a.py")
    write_module(tmp_path / "services" / "payment_b.py")

    violations = collect_violations([tmp_path])

    assert not [key for key in violations if key.startswith("A|")]


def test_size_rule_flags_a_module_over_the_ceiling(tmp_path: pathlib.Path) -> None:
    huge = write_module(tmp_path / "services" / "huge.py", "\n" * (MAX_FILE_LOC + 1))

    assert f"B|{huge.as_posix()}" in collect_violations([tmp_path])


def test_keyword_package_rule_flags_reserved_names(tmp_path: pathlib.Path) -> None:
    package = tmp_path / "services" / "import"
    write_module(package / "__init__.py")

    assert f"C|{package.as_posix()}" in collect_violations([tmp_path])


def test_package_repetition_rule_flags_a_prefixed_module(tmp_path: pathlib.Path) -> None:
    module = write_module(tmp_path / "handlers" / "expense_handler.py")

    assert f"D|{module.as_posix()}" in collect_violations([tmp_path])


def test_package_surface_rule_flags_all_in_an_internal_init(tmp_path: pathlib.Path) -> None:
    init = write_module(tmp_path / "services" / "__init__.py", '__all__ = ["Service"]\n')

    assert f"E|{init.as_posix()}" in collect_violations([tmp_path])
