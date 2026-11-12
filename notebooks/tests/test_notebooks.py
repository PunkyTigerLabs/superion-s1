"""Execute every notebook top to bottom against the real API.

Needs SUPERION_API_KEY and S1_LIVE=1. Before superion-s1 is on PyPI, install it first
(pip install -e ../python) and set NB_SKIP_PIP=1 to skip the %pip cell.
"""
import os
import pathlib

import nbformat
import pytest
from nbclient import NotebookClient

NOTEBOOKS = sorted((pathlib.Path(__file__).resolve().parents[1]).glob("*.ipynb"))


def test_notebooks_are_valid_and_have_no_outputs_or_keys():
    for p in NOTEBOOKS:
        nb = nbformat.read(p, as_version=4)
        nbformat.validate(nb)
        for c in nb.cells:
            assert "s1k_" not in c.source.replace("s1k_…", "")
            if c.cell_type == "code":
                assert not c.outputs, f"{p.name}: clear outputs before committing"


@pytest.mark.skipif(not (os.environ.get("S1_LIVE") and os.environ.get("SUPERION_API_KEY")), reason="live")
@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_runs(path):
    nb = nbformat.read(path, as_version=4)
    if os.environ.get("NB_SKIP_PIP"):
        nb.cells = [c for c in nb.cells if not c.source.startswith("%pip")]
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    text = "\n".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.outputs)
    assert "input tokens" in text
