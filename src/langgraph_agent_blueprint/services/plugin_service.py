"""External plugin install, discovery, and contribution service."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models.base import dump_model
from langgraph_agent_blueprint.models.hooks import HookContribution, HookRuntimeMetadata
from langgraph_agent_blueprint.models.plugins import PluginContribution, PluginInstallResult, PluginManifest, PluginPolicyContribution, PluginSource
from langgraph_agent_blueprint.plugins.superpowers import (
    SUPERPOWERS_BOOTSTRAP_SKILL,
    SUPERPOWERS_PLUGIN_NAME,
    is_superpowers_repo,
    superpowers_bootstrap_context,
    superpowers_policy_contribution,
)
from langgraph_agent_blueprint.utils.paths import ensure_dir


class PluginService:
    """Discovers external plugin manifests and exposes safe data-only contributions."""

    def __init__(
        self,
        plugin_paths: list[str | Path],
        storage_dir: str | Path = ".storage",
        network_enabled: bool = False,
        git_timeout_seconds: float = 60.0,
    ) -> None:
        self.plugin_paths = [Path(path) for path in plugin_paths]
        self.storage_dir = Path(storage_dir)
        self.network_enabled = network_enabled
        self.git_timeout_seconds = git_timeout_seconds
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
        hooks = []
        policies = []
        hook_warnings: list[dict[str, str]] = []
        policy_warnings: list[dict[str, str]] = []
        fragments: list[str] = []
        for contribution in contributions:
            skill_names = self._skill_registry_ids(contribution)
            hook_payloads = [hook.model_dump(mode="json", exclude_none=True) for hook in contribution.hooks]
            policy_payloads = [policy.model_dump(mode="json", exclude_none=True) for policy in contribution.policies]
            plugins.append(
                {
                    **contribution.manifest.model_dump(mode="json", exclude_none=True),
                    "name": contribution.plugin_name,
                    "enabled": True,
                    "root_path": contribution.root_path,
                    "skills_path": contribution.skills_path,
                    "bootstrap_skill": contribution.bootstrap_skill,
                    "skills_count": len(skill_names),
                    "hooks_count": len(contribution.hooks),
                    "policies_count": len(contribution.policies),
                    "hook_warnings": contribution.hook_warnings,
                    "policy_warnings": contribution.policy_warnings,
                }
            )
            skills.extend(skill_names)
            hooks.extend(hook_payloads)
            policies.extend(policy_payloads)
            hook_warnings.extend(contribution.hook_warnings)
            policy_warnings.extend(contribution.policy_warnings)
            fragments.extend(contribution.system_context_fragments)
        return {
            "plugins": plugins,
            "contributions": [contribution.model_dump(mode="json", exclude_none=True) for contribution in contributions],
            "errors": errors,
            "commands": [],
            "skills": skills,
            "tools": [],
            "hooks": hooks,
            "policies": policies,
            "hook_warnings": hook_warnings,
            "policy_warnings": policy_warnings,
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
        hooks_declared, manifest_hook_warnings = self._manifest_hook_entries(name, codex, claude)
        hooks, parse_hook_warnings = self._parse_hooks(root_path, name, hooks_declared)
        policies_declared, manifest_policy_warnings = self._manifest_policy_entries(name, codex, claude)
        policies, parse_policy_warnings = self._parse_policies(name, policies_declared)
        hook_warnings = [*manifest_hook_warnings, *parse_hook_warnings]
        policy_warnings = [*manifest_policy_warnings, *parse_policy_warnings]
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
                "hooks": hooks_declared,
                "policies": policies_declared,
            }
        )
        contribution = PluginContribution(
            plugin_name=name,
            root_path=str(root_path),
            manifest=manifest,
            skills_path=str(skills_path) if skills_path else None,
            bootstrap_skill=bootstrap_skill,
            system_context_fragments=[],
            hooks=hooks,
            hook_warnings=hook_warnings,
            policies=policies,
            policy_warnings=policy_warnings,
        )
        if is_superpowers_repo(root_path, name) and skills_path:
            skill_names = self._skill_registry_ids(contribution)
            contribution = contribution.model_copy(
                update={
                    "system_context_fragments": [superpowers_bootstrap_context(contribution, skill_names)],
                    "policies": [*contribution.policies, superpowers_policy_contribution()],
                }
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
                self._run_git(["git", "-C", str(repo_target), "fetch", "--all", "--tags"], phase="fetch")
            else:
                self._run_git(["git", "clone", "--no-recurse-submodules", git_url, str(repo_target)], phase="clone")
            checkout_ref = source.ref or "main"
            self._run_git(["git", "-C", str(repo_target), "checkout", checkout_ref], phase="checkout")
            resolved_commit = self._run_git(["git", "-C", str(repo_target), "rev-parse", "HEAD"], phase="rev-parse").strip()
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

    @staticmethod
    def _manifest_hook_entries(plugin_name: str, *manifests: dict[str, Any]) -> tuple[list[Any], list[dict[str, str]]]:
        entries: list[Any] = []
        warnings: list[dict[str, str]] = []
        for manifest in manifests:
            if "hooks" not in manifest:
                continue
            raw_hooks = manifest.get("hooks")
            if raw_hooks is None:
                continue
            if not isinstance(raw_hooks, list):
                warnings.append({"plugin": plugin_name, "hook": "hooks", "error": "plugin hooks field must be a list"})
                continue
            entries.extend(raw_hooks)
        return entries, warnings

    def _parse_hooks(self, root_path: Path, plugin_name: str, raw_hooks: list[Any]) -> tuple[list[HookContribution], list[dict[str, str]]]:
        hooks: list[HookContribution] = []
        warnings: list[dict[str, str]] = []
        source_path = str(root_path / ".codex-plugin" / "plugin.json")
        for index, raw in enumerate(raw_hooks):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("plugin hook entry must be an object")
                hook_point = raw.get("hook_point") or raw.get("point")
                hook_id = str(raw.get("id") or f"{plugin_name}.{hook_point}.{index}")
                runtime = HookRuntimeMetadata(
                    action=raw.get("action", "continue"),
                    content=raw.get("content"),
                    event_type=raw.get("event_type"),
                    event_data=raw.get("event_data") if isinstance(raw.get("event_data"), dict) else {},
                    metadata_update=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
                    context_update=raw.get("context") if isinstance(raw.get("context"), dict) else {},
                    block_reason=raw.get("message") or raw.get("reason"),
                )
                hooks.append(
                    HookContribution(
                        id=hook_id,
                        plugin_name=plugin_name,
                        hook_point=hook_point,
                        description=raw.get("description"),
                        enabled=bool(raw.get("enabled", True)),
                        priority=int(raw.get("priority", 100)),
                        trusted=False,
                        source_path=source_path,
                        metadata={"runtime": runtime.model_dump(mode="json", exclude_none=True)},
                    )
                )
            except Exception as exc:
                warnings.append({"plugin": plugin_name, "hook": str(raw.get("id", index)) if isinstance(raw, dict) else str(index), "error": str(exc)})
        return hooks, warnings

    @staticmethod
    def _manifest_policy_entries(plugin_name: str, *manifests: dict[str, Any]) -> tuple[list[Any], list[dict[str, str]]]:
        entries: list[Any] = []
        warnings: list[dict[str, str]] = []
        for manifest in manifests:
            if "policies" not in manifest:
                continue
            raw_policies = manifest.get("policies")
            if raw_policies is None:
                continue
            if not isinstance(raw_policies, list):
                warnings.append({"plugin": plugin_name, "policy": "policies", "error": "plugin policies field must be a list"})
                continue
            entries.extend(raw_policies)
        return entries, warnings

    @staticmethod
    def _parse_policies(plugin_name: str, raw_policies: list[Any]) -> tuple[list[PluginPolicyContribution], list[dict[str, str]]]:
        policies: list[PluginPolicyContribution] = []
        warnings: list[dict[str, str]] = []
        for index, raw in enumerate(raw_policies):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("plugin policy entry must be an object")
                policy_id = str(raw.get("id") or f"{plugin_name}.policy.{index}")
                metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
                if raw.get("skill") or raw.get("skill_name") or raw.get("match_any") or raw.get("match_all") or raw.get("terms"):
                    metadata = {
                        **metadata,
                        "rules": [
                            {
                                "skill_name": raw.get("skill_name") or raw.get("skill"),
                                "match_any": raw.get("match_any") or raw.get("terms") or [],
                                "match_all": raw.get("match_all") or [],
                                "reason": raw.get("reason"),
                                "once_per_session": raw.get("once_per_session", True),
                            }
                        ],
                    }
                policies.append(
                    PluginPolicyContribution(
                        id=policy_id,
                        plugin_name=plugin_name,
                        priority=int(raw.get("priority", 100)),
                        enabled=bool(raw.get("enabled", True)),
                        policy_type=raw.get("policy_type") or raw.get("type") or "skill_activation",
                        metadata=metadata,
                    )
                )
            except Exception as exc:
                warnings.append({"plugin": plugin_name, "policy": str(raw.get("id", index)) if isinstance(raw, dict) else str(index), "error": str(exc)})
        return policies, warnings

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

    def _run_git(self, args: list[str], *, phase: str) -> str:
        try:
            result = subprocess.run(args, check=False, text=True, capture_output=True, timeout=self.git_timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"git {phase} timed out after {self.git_timeout_seconds:g} seconds") from exc
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
