"""Prototype static security checks for a HACS integration repository.

Reads files only (ast.parse, byte reads). Never imports or runs scanned code.
Usage: python -I scan.py <repo_dir> [<repo_dir> ...] > out.json
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

BINARY_MAGIC = {
    b"\x7fELF": "ELF",
    b"MZ": "PE",
    b"\xcf\xfa\xed\xfe": "Mach-O",
    b"\xfe\xed\xfa\xcf": "Mach-O",
    b"PK\x03\x04": "zip",
}
BINARY_EXT = {".so", ".pyd", ".dll", ".exe", ".dylib", ".whl", ".zip", ".pyc", ".bin", ".jar"}
B64_RE = re.compile(r"^[A-Za-z0-9+/=]{300,}$")
URL_RE = re.compile(r"^(https?|wss?)://([^/:\s]+)")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "example.com", "github.com",
               "www.home-assistant.io", "home-assistant.io", "developers.home-assistant.io"}

SUBPROCESS_CALLS = {
    "subprocess.run", "subprocess.call", "subprocess.check_call", "subprocess.check_output",
    "subprocess.Popen", "subprocess.getoutput", "subprocess.getstatusoutput",
    "os.system", "os.popen", "os.execv", "os.execvp", "os.spawnl", "os.spawnv",
    "asyncio.create_subprocess_exec", "asyncio.create_subprocess_shell",
}
DESERIALISE_CALLS = {"pickle.load", "pickle.loads", "marshal.load", "marshal.loads",
                     "dill.load", "dill.loads", "shelve.open", "yaml.unsafe_load",
                     "jsonpickle.decode"}
PKG_INSTALL_CALLS = {"homeassistant.util.package.install_package", "install_package",
                     "pip.main", "pip._internal.main"}


def dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


class Visitor(ast.NodeVisitor):
    def __init__(self, rel: str, aliases: dict[str, str]) -> None:
        self.rel = rel
        self.aliases = aliases
        self.findings: list[dict] = []
        self.hosts: set[str] = set()
        self.view_stack: list[bool] = []

    def add(self, check: str, node: ast.AST, detail: str, sev: str) -> None:
        self.findings.append({"check": check, "sev": sev, "file": self.rel,
                              "line": getattr(node, "lineno", 0), "detail": detail})

    def resolve(self, name: str) -> str:
        head, _, rest = name.partition(".")
        if head in self.aliases:
            return self.aliases[head] + ("." + rest if rest else "")
        return name

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = {self.resolve(dotted(b)).split(".")[-1] for b in node.bases}
        if any(b.endswith("SafeLoader") for b in bases):
            SAFE_LOADERS.add(node.name)
        is_view = "HomeAssistantView" in bases
        if is_view:
            unauth = False
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if (isinstance(t, ast.Name) and t.id == "requires_auth"
                                and isinstance(stmt.value, ast.Constant)
                                and stmt.value.value is False):
                            unauth = True
            if unauth:
                self.add("http_view_no_auth", node, f"class {node.name}: requires_auth = False", "high")
            else:
                self.add("http_view", node, f"class {node.name}", "info")
        self.view_stack.append(is_view)
        self.generic_visit(node)
        self.view_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = self.resolve(dotted(node.func))
        short = name.split(".")[-1]
        kw = {k.arg: k.value for k in node.keywords if k.arg}

        if name in SUBPROCESS_CALLS:
            shell = isinstance(kw.get("shell"), ast.Constant) and kw["shell"].value is True
            sev = "high" if shell or name.endswith(("_shell", "system", "popen")) else "medium"
            self.add("subprocess", node, name + (" shell=True" if shell else ""), sev)
        if name in {"eval", "exec", "compile"} or (name == "__import__" and node.args
                                                   and not isinstance(node.args[0], ast.Constant)):
            self.add("dynamic_code", node, name, "high")
        if short == "eval" and name != "eval":
            self.add("dynamic_code", node, f"{name}() (embedded interpreter)", "medium")
        if name in {"importlib.import_module"} and node.args and not isinstance(node.args[0], ast.Constant):
            self.add("dynamic_import", node, name + "(non-constant)", "low")
        if name in DESERIALISE_CALLS:
            self.add("unsafe_deserialise", node, name, "high")
        if name == "yaml.load":
            loader = kw.get("Loader") or (node.args[1] if len(node.args) > 1 else None)
            lname = dotted(loader) if loader is not None else ""
            if not (lname.endswith(("SafeLoader", "BaseLoader")) or lname.split(".")[-1] in SAFE_LOADERS):
                self.add("unsafe_deserialise", node, f"yaml.load Loader={lname or 'default'}", "high")
        # TLS verification disabled
        for key in ("verify", "verify_ssl", "ssl"):
            v = kw.get(key)
            if isinstance(v, ast.Constant) and v.value is False:
                self.add("tls_verify_off", node, f"{short}({key}=False)", "medium")
        if name.endswith("_create_unverified_context"):
            self.add("tls_verify_off", node, name, "medium")
        if name.endswith("webhook.async_register") or short == "async_register_webhook":
            self.add("webhook", node, name, "info")
        if name in PKG_INSTALL_CALLS or short == "install_package":
            self.add("runtime_pkg_install", node, name, "high")
        if short == "add_extra_js_url" or (short == "async_create_item" and "res_type" in ast.unparse(node)):
            self.add("frontend_injection", node, name, "medium")
        if name == "bytes.fromhex" and node.args and "b64decode" in ast.unparse(node.args[0]):
            self.add("obfuscation", node, "bytes.fromhex(b64decode(...)) string hiding", "medium")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "CERT_NONE":
            self.add("tls_verify_off", node, dotted(node), "medium")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for t in node.targets:
            if (isinstance(t, ast.Attribute) and t.attr == "check_hostname"
                    and isinstance(node.value, ast.Constant) and node.value.value is False):
                self.add("tls_verify_off", node, "check_hostname = False", "medium")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            s = node.value.strip()
            if B64_RE.match(s):
                self.add("obfuscation", node, f"base64-like literal, {len(s)} chars", "medium")
            m = URL_RE.match(s)
            if m:
                host = m.group(2).lower()
                if host not in LOCAL_HOSTS and "{" not in host and "%" not in host:
                    self.hosts.add(host)


SAFE_LOADERS: set[str] = set()
# Conventional Home Assistant short aliases (er = entity_registry, cv = config_validation, ...)
HA_ALIASES = {"ar", "cr", "dr", "er", "fr", "ir", "lr", "cv", "dt", "vol", "pd"}


def short_alias_count(tree: ast.AST) -> int:
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            n += sum(1 for a in node.names
                     if a.asname and len(a.asname) <= 2 and a.asname not in HA_ALIASES)
    return n


def collect_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                aliases[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                aliases[a.asname or a.name] = f"{node.module}.{a.name}"
    return aliases


def scan_repo(repo: Path) -> dict:
    cc = repo / "custom_components"
    domains = [d for d in cc.iterdir() if d.is_dir()] if cc.is_dir() else []
    result: dict = {"repo": repo.name, "domains": [d.name for d in domains], "findings": [],
                    "hosts": [], "manifest": {}, "py_files": 0, "py_lines": 0, "parse_errors": []}
    hosts: set[str] = set()
    SAFE_LOADERS.clear()
    for d in domains:  # pre-pass: local yaml.SafeLoader subclasses
        for f in d.rglob("*.py"):
            try:
                t = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(t):
                if isinstance(n, ast.ClassDef) and any(dotted(x).endswith("SafeLoader") for x in n.bases):
                    SAFE_LOADERS.add(n.name)
    for d in domains:
        mf = d / "manifest.json"
        if mf.is_file():
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
                result["manifest"][d.name] = {k: m.get(k) for k in
                                              ("version", "requirements", "iot_class", "dependencies",
                                               "after_dependencies", "codeowners")}
            except ValueError as err:
                result["parse_errors"].append(f"{mf}: {err}")
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(repo).as_posix()
            head = f.open("rb").read(4)
            kind = next((v for k, v in BINARY_MAGIC.items() if head.startswith(k)), None)
            if f.suffix.lower() in BINARY_EXT or kind:
                result["findings"].append({"check": "bundled_binary", "sev": "high", "file": rel,
                                           "line": 0, "detail": kind or f.suffix})
            if f.suffix != ".py":
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            result["py_files"] += 1
            result["py_lines"] += src.count("\n") + 1
            if any(len(line) > 2000 for line in src.splitlines()):
                result["findings"].append({"check": "obfuscation", "sev": "medium", "file": rel,
                                           "line": 0, "detail": "line over 2000 chars"})
            try:
                tree = ast.parse(src, filename=rel)
            except SyntaxError as err:
                result["parse_errors"].append(f"{rel}: {err}")
                continue
            if (sa := short_alias_count(tree)) >= 5:
                result["findings"].append({"check": "obfuscation", "sev": "medium", "file": rel,
                                           "line": 0, "detail": f"{sa} imports renamed to 1-2 letters"})
            v = Visitor(rel, collect_aliases(tree))
            v.visit(tree)
            result["findings"].extend(v.findings)
            hosts |= v.hosts
    result["hosts"] = sorted(hosts)
    return result


if __name__ == "__main__":
    out = [scan_repo(Path(p)) for p in sys.argv[1:]]
    json.dump(out, sys.stdout, indent=1)
