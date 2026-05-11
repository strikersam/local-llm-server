import pytest
from pathlib import Path
from agent.repowise import RepowiseIntelligence

@pytest.fixture
def repowise(tmp_path):
    # Create a structure with FastAPI-like keywords
    """
    Create a temporary repository structure with example FastAPI and React files and return a RepowiseIntelligence instance pointed at it.
    
    Parameters:
        tmp_path (pathlib.Path): Temporary directory provided by pytest; used as the root for the generated repository tree. The fixture creates `api/` (server.py, router.py, models.py) and `web/` (App.js, utils.js, hooks.js).
    
    Returns:
        RepowiseIntelligence: An instance initialized to analyze the generated temporary repository.
    """
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef read_root(): return {'Hello': 'World'}")
    (tmp_path / "api" / "router.py").write_text("def route(): pass")
    (tmp_path / "api" / "models.py").write_text("class User: pass")

    # Create a structure with React-like keywords
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "App.js").write_text("import React, { useState } from 'react';\nfunction App() { return <div></div>; }")
    (tmp_path / "web" / "utils.js").write_text("def util(): pass")
    (tmp_path / "web" / "hooks.js").write_text("def hook(): pass")

    return RepowiseIntelligence(tmp_path)

def test_get_architecture_summary(repowise):
    summary = repowise.get_architecture_summary()
    assert "key_modules" in summary
    assert "patterns" in summary

    module_names = [m["name"] for m in summary["key_modules"]]
    assert "api" in module_names
    assert "web" in module_names

    assert "FastAPI/REST" in summary["patterns"]
    assert "React/Frontend" in summary["patterns"]

def test_get_context_token_estimation(repowise):
    context = repowise.get_context(["api/server.py"])
    assert "Estimated total tokens:" in context

def test_extract_symbol_v2(repowise):
    # Test class extraction
    context = repowise.get_context(["User:api/models.py"])
    assert "class User: pass" in context

    # Test function extraction
    context = repowise.get_context(["read_root:api/server.py"])
    assert "def read_root():" in context
