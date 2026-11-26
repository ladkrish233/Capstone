from app.agent import builder


def test_agent_has_no_delete_tool(monkeypatch):
    # Rule: only the HTTP route may delete; the agent never can.
    monkeypatch.setattr(builder, "MODEL", "test")
    names = builder.build_agent().__dict__["_function_toolset"].tools.keys()
    assert not [n for n in names if "delete" in n or "remove" in n]
    assert "add_reminder" in names
