from __future__ import annotations

import inspect
from typing import Any, Callable


class ToolsRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._approval_required: set[str] = set()

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        schema: dict[str, Any],
        *,
        approval_required: bool = False,
    ) -> None:
        tool_name = str(name or "").strip()
        if not tool_name:
            raise ValueError("tool name is required")
        self._tools[tool_name] = {"func": func, "schema": schema}
        if approval_required:
            self._approval_required.add(tool_name)

    def execute(self, name: str, params: dict[str, Any] | None = None, **extra: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        tool = self._tools[name]["func"]
        merged = dict(extra)
        merged.update(params or {})
        sig = inspect.signature(tool)
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if accepts_kwargs:
            return tool(**merged)
        filtered = {key: value for key, value in merged.items() if key in sig.parameters}
        return tool(**filtered)

    def schemas(self) -> list[dict[str, Any]]:
        return [self._tools[name]["schema"] for name in sorted(self._tools)]

    def requires_approval(self, name: str) -> bool:
        return str(name or "").strip() in self._approval_required

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> list[dict[str, Any]]:
        itens: list[dict[str, Any]] = []
        for name in sorted(self._tools):
            schema = dict(self._tools[name]["schema"])
            itens.append(
                {
                    "name": name,
                    "approval_required": name in self._approval_required,
                    "schema": schema,
                }
            )
        return itens
