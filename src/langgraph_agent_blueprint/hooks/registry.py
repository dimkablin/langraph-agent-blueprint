"""Hook contribution registry."""

from __future__ import annotations

from collections import defaultdict

from langgraph_agent_blueprint.models.hooks import HookContribution, HookPoint


class HookRegistry:
    """Registry for core and plugin hook contributions."""

    def __init__(self) -> None:
        self._hooks: dict[str, HookContribution] = {}

    def register(self, contribution: HookContribution, *, replace: bool = False) -> None:
        """Register one contribution, rejecting duplicate ids by default."""

        if contribution.id in self._hooks and not replace:
            raise ValueError(f"Duplicate hook id: {contribution.id}")
        self._hooks[contribution.id] = contribution

    def get(self, hook_id: str) -> HookContribution:
        """Return one hook contribution by id."""

        try:
            return self._hooks[hook_id]
        except KeyError as exc:
            raise KeyError(f"Unknown hook: {hook_id}") from exc

    def set_enabled(self, hook_id: str, enabled: bool) -> None:
        """Enable or disable a registered hook."""

        current = self.get(hook_id)
        self._hooks[hook_id] = current.model_copy(update={"enabled": enabled})

    def get_for_point(self, hook_point: HookPoint, *, include_disabled: bool = False) -> list[HookContribution]:
        """Return hooks for one lifecycle point sorted by priority then id."""

        hooks = [hook for hook in self._hooks.values() if hook.hook_point == hook_point]
        if not include_disabled:
            hooks = [hook for hook in hooks if hook.enabled]
        return sorted(hooks, key=lambda hook: (hook.priority, hook.id))

    def list_hooks(self, *, include_disabled: bool = True) -> list[HookContribution]:
        """Return all hooks sorted by priority then id."""

        hooks = list(self._hooks.values())
        if not include_disabled:
            hooks = [hook for hook in hooks if hook.enabled]
        return sorted(hooks, key=lambda hook: (hook.priority, hook.id))

    def group_by_plugin(self) -> dict[str, list[HookContribution]]:
        """Group hooks by plugin name for diagnostics."""

        grouped: dict[str, list[HookContribution]] = defaultdict(list)
        for hook in self.list_hooks():
            grouped[hook.plugin_name or "core"].append(hook)
        return dict(grouped)

    def snapshot(self) -> list[dict]:
        """Return graph-state-safe hook metadata."""

        return [hook.model_dump(mode="json", exclude_none=True) for hook in self.list_hooks()]

