"""Executable boundaries for this small toolkit; no production framework needed."""

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "TOOLS"
CORE = TOOLS / "novel_to_comic"
PACKAGE = "novel_to_comic"

# Adding a module or a dependency is an explicit architecture decision. These
# are allowed edges, not mandatory imports; unused dependencies need no stubs.
ALLOWED_DEPENDENCIES = {
    "__init__": set(),
    "artifacts": set(),
    "bind": set(),
    "compose": {"artifacts", "config", "layout"},
    "config": {"artifacts"},
    "director_briefs": {"validation"},
    "image_tasks": {"artifacts", "config"},
    "layout": set(),
    "lettering": {"artifacts", "config", "layout"},
    "page_script": {"validation"},
    "page_story_plan": {"validation"},
    "qc": {"artifacts", "config"},
    "source": {"artifacts"},
    "state": {"page_script", "page_story_plan", "validation"},
    "validation": {"artifacts"},
}
IMAGE_MODULES = {"bind", "compose", "lettering", "qc"}
FORBIDDEN_IMPORTS = {
    "argparse", "subprocess", "multiprocessing", "concurrent", "asyncio",
    "socket", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp",
    "ftplib", "smtplib", "telnetlib", "websockets",
}
PROCESS_FUNCTIONS = {"system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp"}
PRODUCTION_DIMENSIONS = {2048, 2480, 3508}


def imported_names(tree, module):
    """Resolve static import spelling without importing any inspected module."""
    package = PACKAGE
    if "." in module:
        package += "." + module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = importlib.util.resolve_name("." * node.level + base, package)
            if base == PACKAGE:
                for alias in node.names:
                    yield f"{base}.{alias.name}"
            else:
                yield base
                if base == "os":
                    for alias in node.names:
                        yield f"os.{alias.name}"


def import_aliases(tree, module):
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                aliases[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = PACKAGE + ("." + module.rpartition(".")[0] if "." in module else "")
                try:
                    base = importlib.util.resolve_name("." * node.level + base, package)
                except ImportError:
                    # The dependency check reports escaping relative imports.
                    continue
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{base}.{alias.name}"
    return aliases


def qualified_name(node, aliases):
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = qualified_name(node.value, aliases)
        return f"{base}.{node.attr}" if base else ""
    return ""


def is_process_function(name):
    if not name.startswith("os."):
        return False
    member = name.removeprefix("os.")
    return member in PROCESS_FUNCTIONS or member.startswith(("exec", "spawn"))


def find_cycle(graph):
    visited = set()
    active = []

    def visit(module):
        if module in active:
            return active[active.index(module):] + [module]
        if module in visited:
            return None
        active.append(module)
        for dependency in sorted(graph[module]):
            if dependency in graph:
                cycle = visit(dependency)
                if cycle:
                    return cycle
        active.pop()
        visited.add(module)
        return None

    for module in sorted(graph):
        cycle = visit(module)
        if cycle:
            return cycle
    return None


def source_violations(source, module, *, cli=False):
    tree = ast.parse(source)
    aliases = import_aliases(tree, module)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "_layout_boxes" or node.name.endswith("_page_numbers"):
                problems.append(f"{module}: retired helper {node.name}")
            if node.name == "panel_boxes" and module != "layout":
                problems.append(f"{module}: panel geometry belongs to layout")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value in PRODUCTION_DIMENSIONS and module != "config":
                problems.append(f"{module}: production dimension {node.value} belongs to config")
        if not isinstance(node, ast.Call):
            continue
        name = qualified_name(node.func, aliases)
        if name in {"__import__", "builtins.__import__", "importlib.import_module"}:
            problems.append(f"{module}: dynamic imports hide dependency edges")
        if not cli and is_process_function(name):
            problems.append(f"{module}: process execution is outside the core")
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes"}:
            canonical = name in {"artifacts.write_text", "novel_to_comic.artifacts.write_text"}
            if module != "artifacts" and not canonical:
                problems.append(f"{module}: text persistence belongs to artifacts")
        if name in {"json.load", "json.loads", "json.dump", "json.dumps", "json.JSONDecoder", "json.JSONEncoder"}:
            if module == "artifacts" and not cli:
                continue
            parent = parents.get(node)
            stdout = (
                cli and name == "json.dumps" and isinstance(parent, ast.Call)
                and qualified_name(parent.func, aliases) in {"print", "builtins.print"}
                and node in parent.args and not any(keyword.arg == "file" for keyword in parent.keywords)
            )
            if not stdout:
                problems.append(f"{module}: JSON persistence belongs to artifacts")
    return problems


def architecture_violations(sources, allowed, command_names=()):
    problems = []
    graph = {module: set() for module in sources}
    for module in sorted(set(sources) ^ set(allowed)):
        problems.append(f"{module}: module inventory and architecture map disagree")
    for module, source in sorted(sources.items()):
        tree = ast.parse(source)
        problems.extend(source_violations(source, module))
        if any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
               for node in ast.walk(tree)):
            problems.append(f"{module}: wildcard imports hide public contracts")
        try:
            imports = list(imported_names(tree, module))
        except ImportError:
            problems.append(f"{module}: relative import escapes the core package")
            continue
        for imported in imports:
            root = imported.split(".")[0]
            if imported == PACKAGE or imported.startswith(PACKAGE + "."):
                dependency = imported.removeprefix(PACKAGE + ".") if imported != PACKAGE else "__init__"
                graph[module].add(dependency)
                if dependency not in allowed.get(module, set()):
                    problems.append(f"{module} -> {dependency}: unapproved dependency")
            elif root in command_names or root == "TOOLS":
                problems.append(f"{module}: core cannot import command adapter {imported}")
            elif root in FORBIDDEN_IMPORTS or is_process_function(imported):
                problems.append(f"{module}: forbidden core import {imported}")
            elif root == "PIL":
                if module not in IMAGE_MODULES:
                    problems.append(f"{module}: Pillow belongs to image services")
            elif root not in sys.stdlib_module_names:
                problems.append(f"{module}: unapproved external dependency {imported}")
    cycle = find_cycle(graph)
    if cycle:
        problems.append("dependency cycle: " + " -> ".join(cycle))
    return problems


class ArchitectureTests(unittest.TestCase):
    def test_package_dependencies_and_authoritative_implementations(self):
        sources = {
            path.relative_to(CORE).with_suffix("").as_posix().replace("/", "."): path.read_text(encoding="utf-8")
            for path in CORE.rglob("*.py")
        }
        commands = {path.stem for path in TOOLS.glob("*.py")}
        problems = architecture_violations(sources, ALLOWED_DEPENDENCIES, commands)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_command_adapters_do_not_reintroduce_domain_helpers_or_json_io(self):
        problems = []
        for path in TOOLS.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            problems.extend(source_violations(source, path.stem, cli=True))
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name != "main":
                    problems.append(f"{path.name}: business implementation belongs in the package ({node.name})")
        self.assertEqual(problems, [], "\n".join(problems))


class ArchitectureGuardTests(unittest.TestCase):
    def test_relative_and_absolute_edges_cannot_bypass_direction(self):
        for statement in (
            "from .artifacts import read_json", "from . import artifacts",
            "from novel_to_comic.artifacts import read_json", "import novel_to_comic.artifacts as store",
            "from novel_to_comic import artifacts",
        ):
            with self.subTest(statement=statement):
                problems = architecture_violations({"layout": statement, "artifacts": ""}, {"layout": set(), "artifacts": set()})
                self.assertIn("layout -> artifacts: unapproved dependency", problems)

    def test_cycles_are_rejected_even_when_each_edge_is_allowed(self):
        sources = {"a": "from . import b", "b": "from novel_to_comic.a import value"}
        problems = architecture_violations(sources, {"a": {"b"}, "b": {"a"}})
        self.assertIn("dependency cycle: a -> b -> a", problems)
        self.assertIsNone(find_cycle({"a": {"b"}, "b": set()}))

    def test_new_modules_wildcards_and_escaping_imports_need_explicit_decisions(self):
        problems = architecture_violations({"new_service": ""}, {})
        self.assertIn("new_service: module inventory and architecture map disagree", problems)
        problems = architecture_violations({"layout": "from math import *"}, {"layout": set()})
        self.assertIn("layout: wildcard imports hide public contracts", problems)
        problems = architecture_violations({"layout": "from .. import check_state"}, {"layout": set()})
        self.assertIn("layout: relative import escapes the core package", problems)

    def test_core_cannot_pull_in_commands_processes_network_or_images(self):
        for statement, expected in (
            ("import check_state", "command adapter"),
            ("from TOOLS import check_state", "command adapter"),
            ("import argparse", "forbidden core import"),
            ("import subprocess as runner", "forbidden core import"),
            ("from urllib.request import urlopen", "forbidden core import"),
            ("from os import system as run", "forbidden core import"),
            ("import os as operating; operating.system('true')", "process execution"),
            ("from PIL import Image", "Pillow belongs"),
        ):
            with self.subTest(statement=statement):
                problems = architecture_violations({"layout": statement}, {"layout": set()}, {"check_state"})
                self.assertTrue(any(expected in problem for problem in problems), problems)

    def test_json_aliases_and_file_outputs_cannot_bypass_artifact_boundary(self):
        for source in (
            "import json as codec; codec.loads('{}')",
            "from json import loads as decode; decode('{}')",
            "import json; json.dump({}, handle)",
            "import json; target.write_text(json.dumps({}))",
            "import json; print(json.dumps({}), file=handle)",
        ):
            with self.subTest(source=source):
                self.assertTrue(any("JSON persistence" in issue for issue in source_violations(source, "command", cli=True)))
        self.assertEqual(source_violations("import json; print(json.dumps({}))", "command", cli=True), [])
        self.assertEqual(source_violations("import json; error = json.JSONDecodeError", "validation"), [])
        self.assertEqual(source_violations("import json; json.loads('{}')", "artifacts"), [])
        self.assertTrue(any("text persistence" in issue for issue in source_violations("target.write_text('partial')", "source")))
        self.assertTrue(any("text persistence" in issue for issue in source_violations("target.write_bytes(b'partial')", "source")))
        self.assertEqual(source_violations("from novel_to_comic import artifacts; artifacts.write_text(path, 'complete')", "source"), [])
        self.assertEqual(source_violations("from . import artifacts as store; store.write_text(path, 'complete')", "source"), [])

    def test_authoritative_defaults_and_retired_helpers_are_enforced(self):
        for source, expected in (
            ("SIZE = (2480, 3508)", "belongs to config"),
            ("MINIMUM = 2048", "belongs to config"),
            ("def _layout_boxes(): pass", "retired helper"),
            ("def _storyboard_page_numbers(): pass", "retired helper"),
            ("def panel_boxes(): pass", "geometry belongs"),
            ("import importlib as loader; loader.import_module('os')", "dynamic imports"),
        ):
            with self.subTest(source=source):
                self.assertTrue(any(expected in issue for issue in source_violations(source, "state")))
        self.assertEqual(source_violations("SIZE = (2480, 3508)", "config"), [])
        self.assertEqual(source_violations("def panel_boxes(): pass", "layout"), [])


if __name__ == "__main__":
    unittest.main()
