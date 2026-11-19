"""
Execute ``examples/ggtext_tour.ipynb`` from top to bottom.

Needs the ``notebook`` extra (``pip install -e ".[test,notebook]"``);
without it the test is skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")
pytest.importorskip("plotnine")

NOTEBOOK = Path(__file__).resolve().parent.parent / "examples" / "ggtext_tour.ipynb"

pytestmark = [pytest.mark.notebook, pytest.mark.plotnine]


def test_tour_notebook_runs(tmp_path: Path):
    nb = nbformat.read(NOTEBOOK, as_version=4)
    client = nbclient.NotebookClient(
        nb,
        timeout=300,
        kernel_name="python3",
        # run in a scratch folder so nothing is written next to the notebook
        resources={"metadata": {"path": str(tmp_path)}},
    )
    client.execute()  # raises CellExecutionError if any cell fails

    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert code_cells
    errors = [
        out
        for cell in code_cells
        for out in cell.get("outputs", [])
        if out.get("output_type") == "error"
    ]
    assert not errors
    # the tour shows figures; make sure they were produced
    images = [
        out
        for cell in code_cells
        for out in cell.get("outputs", [])
        if "image/png" in out.get("data", {})
    ]
    assert images, "the notebook produced no figures"
