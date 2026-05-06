"""External plugin install, discovery, and contribution service."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models.base import dump_model
from langgraph_agent_blueprint.models.plugins import PluginContribution, PluginInstallResult, PluginManifest, PluginSource
from langgraph_agent_blueprint.plugins.superpowers import (
    SUPERPOWERS_BOOTSTRAP_SKILL,
    SUPERPOWERS_PLUGIN_NAME,
    is_superpowers_repo,
    superpowers_bootstrap_context,
)
from langgraph_agent_blueprint.utils.paths import ensure_dir


class PluginService:
    """Discovers external plugin manifests and exposes safe data-only contributions."""

    def __init__(self, plugin_paths: list[str | Path], storage_dir: str | Path = ".storage", network_enabled: bool = False) -> None:
        self.plugin_paths = [Path(path) for path in plugin_paths]
        self.storage_dir = Path(storage_dir)
        self.network_enabled = network_enabled
        self.plugins_root = self.storage_dir / "plugins"

    def discover(self) -> dict[str, Any]:
        """Discover installed/configured plugins and return graph-state-safe metadata."""

        contributions: list[PluginContribution] = []
        errors: list[dict[str, str]] = []
        for root in self._candidate_roots():
            try:
                contributions.append(self.discover_contribution(root))
            except Exception as exc:
                errors.append({"path": str(root), "error": str(exc)})
        skills = []
        plugins = []
        fragments: list[str] = []
        for contribution in contributions:
            skill_names = self._skill_registry_ids(contribution)
            plugins.append(
                {
                    **contribution.manifest.model_dump(mode="json", exclude_none=True),
                    "name": contribution.plugin_name,
                    "enabled": True,
                    "root_path": contribution.root_path,
                    "skills_path": contribution.skills_path,
                    "bootstrap_skill": contribution.bootstrap_skill,
                    "skills_count": len(skill_names),
                }
            )
            skills.extend(skill_names)
            fragments.extend(contribution.system_context_fragments)
        return {
            "plugins": plugins,
            "contributions": [contribution.model_dump(mode="json", exclude_none=True) for contribution in contributions],
            "errors": errors,
            "commands": [],
            "skills": skills,
            "tools": [],
            "hooks": [],
            "mcp": [],
            "system_context_fragments": fragments,
        }

    def discover_contributions(self) -> list[PluginContribution]:
        """Return typed plugin contributions for dependency wiring."""

        return [PluginContribution.model_validate(item) for item in self.discover()["contributions"]]

    def discover_contribution(self, root: str | Path) -> PluginContribution:
        """Discover one plugin repo/root using known harness manifests and fallbacks."""

        root_path = Path(root).resolve()
        if not root_path.exists() or not root_path.is_dir():
            raise FileNotFoundError(root_path)
        codex = self._read_json(root_path / ".codex-plugin" / "plugin.json")
        claude = self._read_json(root_path / ".claude-plugin" / "plugin.json")
        package = self._read_json(root_path / "package.json")
        name = str(codex.get("name") or package.get("name") or claude.get("name") or root_path.name)
        version = codex.get("version") or package.get("version") or claude.get("version")
        skills_declared = codex.get("skills") or claude.get("skills")
        skills_path = self._resolve_skills_path(root_path, skills_declared)
        bootstrap_skill = codex.get("bootstrap_skill") or claude.get("bootstrap_skill")
        if name == SUPERPOWERS_PLUGIN_NAME and skills_path and (Path(skills_path) / SUPERPOWERS_BOOTSTRAP_SKILL / "SKILL.md").exists():
            bootstrap_skill = SUPERPOWERS_BOOTSTRAP_SKILL
        manifest = PluginManifest.model_validate(
            {
                **claude,
                **package,
                **codex,
                "name": name,
                "version": version,
                "skills_path": skills_declared,
                "bootstrap_skill": bootstrap_skill,
            }
        )
        contribution = PluginContribution(
            plugin_name=name,
            root_path=str(root_path),
            manifest=manifest,
            skills_path=str(skills_path) if skills_path else None,
            bootstrap_skill=bootstrap_skill,
            system_context_fragments=[],
        )
        if is_superpowers_repo(root_path, name) and skills_path:
            skill_names = self._skill_registry_ids(contribution)
            contribution = contribution.model_copy(
                update={"system_context_fragments": [superpowers_bootstrap_context(contribution, skill_names)]}
            )
        return contribution

    def parse_source(self, raw_source: str) -> PluginSource:
        """Parse `name@git+url#ref`, `git+url#ref`, `https://github...`, or local paths."""

        raw = raw_source.strip()
        if not raw:
            raise ValueError("plugin source is empty")
        name: str | None = None
        source = raw
        if "@" in raw and raw.split("@", 1)[1].startswith(("git+", "https://", "http://")):
            name, source = raw.split("@", 1)
        ref: str | None = None
        if "#" in source:
            source, ref = source.split("#", 1)
        if source.startswith("https://github.com/") or source.startswith("http://github.com/"):
            source = f"git+{source}"
        if source.startswith("git+"):
            inferred = name or _repo_name_from_url(source[4:])
            return PluginSource(name=inferred, source=source, ref=ref)
        path = Path(source).expanduser()
        inferred = name or path.name
        return PluginSource(name=inferred, source=str(path), ref=ref)

    def install(self, raw_source: str) -> PluginInstallResult:
        """Install a plugin from a local directory or git source without running plugin scripts."""

        source = self.parse_source(raw_source)
        if source.source.startswith("git+"):
            return self._install_git(source)
        return self._install_local(source)

    def update(self, name: str) -> PluginInstallResult:
        """Update an installed plugin using its lock metadata."""

        lock_path = self.plugins_root / name / "lock.json"
        if not lock_path.exists():
            return PluginInstallResult(plugin_name=name, status="not_found", message=f"Plugin not installed: {name}")
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        source = PluginSource.model_validate(lock["source"])
        result = self.install(_source_to_raw(source))
        return result.model_copy(update={"status": "updated" if result.status == "installed" else result.status})

    def remove(self, name: str) -> PluginInstallResult:
        """Remove one cached plugin directory under plugin storage."""

        target = (self.plugins_root / name).resolve()
        root = self.plugins_root.resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return PluginInstallResult(plugin_name=name, status="error", message="Refusing to remove a path outside plugin storage.")
        if not target.exists():
            return PluginInstallResult(plugin_name=name, status="not_found", message=f"Plugin not installed: {name}")
        shutil.rmtree(target)
        return PluginInstallResult(plugin_name=name, status="removed", message=f"Removed plugin {name}")

    def _install_local(self, source: PluginSource) -> PluginInstallResult:
        source_path = Path(source.source).expanduser().resolve()
        if not source_path.exists():
            return PluginInstallResult(plugin_name=source.name, status="error", message=f"Local plugin path does not exist: {source.source}", source=source)
        try:
            contribution = self.discover_contribution(source_path)
        except Exception as exc:
            return PluginInstallResult(plugin_name=source.name, status="error", message=str(exc), source=source)
        plugin_name = contribution.plugin_name
        plugin_root = ensure_dir(self.plugins_root / plugin_name)
        repo_target = plugin_root / "repo"
        if repo_target.exists():
            shutil.rmtree(repo_target)
        shutil.copytree(source_path, repo_target, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
        installed = self.discover_contribution(repo_target)
        lock_path = self._write_lock(plugin_root, source, installed, resolved_commit=None)
        return PluginInstallResult(
            plugin_name=plugin_name,
            status="installed",
            message=f"Installed plugin {plugin_name}",
            root_path=str(repo_target),
            lock_path=str(lock_path),
            source=source,
            manifest=installed.manifest,
        )

    def _install_git(self, source: PluginSource) -> PluginInstallResult:
        if not self.network_enabled:
            return PluginInstallResult(
                plugin_name=source.name,
                status="error",
                message="Network access is disabled; set NETWORK_ENABLED=true for git plugin install/update.",
                source=source,
            )
        plugin_root = ensure_dir(self.plugins_root / source.name)
        repo_target = plugin_root / "repo"
        git_url = source.source[4:]
        try:
            if repo_target.exists():
                self._run_git(["git", "-C", str(repo_target), "fetch", "--all", "--tags"])
            else:
                self._run_git(["git", "clone", "--no-recurse-submodules", git_url, str(repo_target)])
            checkout_ref = source.ref or "main"
            self._run_git(["git", "-C", str(repo_target), "checkout", checkout_ref])
            resolved_commit = self._run_git(["git", "-C", str(repo_target), "rev-parse", "HEAD"]).strip()
            contribution = self.discover_contribution(repo_target)
            lock_path = self._write_lock(plugin_root, source, contribution, resolved_commit=resolved_commit)
            return PluginInstallResult(
                plugin_name=contribution.plugin_name,
                status="installed",
                message=f"Installed plugin {contribution.plugin_name}",
                root_path=str(repo_target),
                lock_path=str(lock_path),
                source=source,
                manifest=contribution.manifest,
                resolved_commit=resolved_commit,
            )
        except Exception as exc:
            return PluginInstallResult(plugin_name=source.name, status="error", message=str(exc), source=source)

    def _candidate_roots(self) -> list[Path]:
        roots: list[Path] = []
        if self.plugins_root.exists():
            roots.extend(path / "repo" for path in self.plugins_root.iterdir() if (path / "repo").is_dir())
        for path in self.plugin_paths:
            if not path.exists():
                continue
            if self._looks_like_plugin_root(path):
                roots.append(path)
            else:
                for child in path.iterdir():
                    if (child / "repo").is_dir():
                        roots.append(child / "repo")
                    elif self._looks_like_plugin_root(child):
                        roots.append(child)
        return _dedupe_paths(roots)

    def _looks_like_plugin_root(self, path: Path) -> bool:
        return any(
            [
                (path / ".codex-plugin" / "plugin.json").exists(),
                (path / ".claude-plugin" / "plugin.json").exists(),
                (path / "package.json").exists() and (path / "skills").is_dir(),
                (path / "skills").is_dir(),
            ]
        )

    def _resolve_skills_path(self, root: Path, declared: Any) -> Path | None:
        if declared:
            if not isinstance(declared, str):
                raise ValueError("plugin skills path must be a string")
            candidate = self._safe_child(root, declared)
            if not candidate.is_dir():
                raise FileNotFoundError(candidate)
            return candidate
        fallback = root / "skills"
        return fallback.resolve() if fallback.is_dir() else None

    def _safe_child(self, root: Path, relative: str) -> Path:
        rel = Path(relative)
        if rel.is_absolute():
            raise ValueError("plugin path traversal rejected: absolute paths are not allowed")
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("plugin path traversal rejected") from exc
        return candidate

    def _skill_registry_ids(self, contribution: PluginContribution) -> list[str]:
        if not contribution.skills_path:
            return []
        skills_path = Path(contribution.skills_path)
        names = [path.name for path in skills_path.iterdir() if path.is_dir() and (path / "SKILL.md").exists()]
        return [f"{contribution.plugin_name}/{name}" for name in sorted(names)]

    def _write_lock(self, plugin_root: Path, source: PluginSource, contribution: PluginContribution, resolved_commit: str | None) -> Path:
        lock_path = plugin_root / "lock.json"
        license_text = self._read_license(Path(contribution.root_path))
        payload = {
            "source": dump_model(source),
            "resolved_commit": resolved_commit,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "manifest": contribution.manifest.model_dump(mode="json", exclude_none=True),
            "license": license_text,
        }
        lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (plugin_root / "manifest.json").write_text(
            json.dumps(contribution.manifest.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return lock_path

    def _read_license(self, root: Path) -> str | None:
        for name in ["LICENSE", "LICENSE.md", "COPYING"]:
            path = root / name
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8", errors="replace")
        return None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _run_git(args: list[str]) -> str:
        result = subprocess.run(args, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "git command failed").strip())
        return result.stdout


def _repo_name_from_url(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def _source_to_raw(source: PluginSource) -> str:
    raw = f"{source.name}@{source.source}"
    return f"{raw}#{source.ref}" if source.ref else raw


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique
