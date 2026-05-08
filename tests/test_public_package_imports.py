"""Public package import surface regression tests."""

from __future__ import annotations


def test_public_package_imports_for_cross_layer_runtime_types() -> None:
    from langgraph_agent_blueprint.context import ContextProviderService, parse_context_references
    from langgraph_agent_blueprint.evals import EvalRunner, load_scenario_by_id
    from langgraph_agent_blueprint.models import (
        ContextReference,
        PluginContextProviderContribution,
        ResolvedContextItem,
        dump_model,
    )
    from langgraph_agent_blueprint.services import FileService, MCPService, WebService
    from langgraph_agent_blueprint.storage import SessionStorage
    from langgraph_agent_blueprint.tools import BaseTool, ToolRegistry

    assert ContextReference.__name__ == "ContextReference"
    assert ResolvedContextItem.__name__ == "ResolvedContextItem"
    assert PluginContextProviderContribution.__name__ == "PluginContextProviderContribution"
    assert FileService.__name__ == "FileService"
    assert MCPService.__name__ == "MCPService"
    assert WebService.__name__ == "WebService"
    assert ContextProviderService.__name__ == "ContextProviderService"
    assert EvalRunner.__name__ == "EvalRunner"
    assert SessionStorage.__name__ == "SessionStorage"
    assert BaseTool.__name__ == "BaseTool"
    assert ToolRegistry.__name__ == "ToolRegistry"
    assert callable(dump_model)
    assert callable(parse_context_references)
    assert callable(load_scenario_by_id)


def test_public_package_exports_are_explicit() -> None:
    import langgraph_agent_blueprint.context as context
    import langgraph_agent_blueprint.evals as evals
    import langgraph_agent_blueprint.models as models
    import langgraph_agent_blueprint.services as services
    import langgraph_agent_blueprint.tools as tools

    assert "ContextReference" in models.__all__
    assert "PluginContextProviderContribution" in models.__all__
    assert "FileService" in services.__all__
    assert "MCPService" in services.__all__
    assert "BaseTool" in tools.__all__
    assert "ContextProviderService" in context.__all__
    assert "EvalRunner" in evals.__all__
