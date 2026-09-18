"""Build and execute the report atomically from project-relative calculations."""

import os
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]
for key, folder in [
    ("MPLCONFIGDIR", "matplotlib"),
    ("IPYTHONDIR", "ipython"),
    ("JUPYTER_CONFIG_DIR", "jupyter"),
    ("JUPYTER_DATA_DIR", "jupyter_data"),
    ("JUPYTER_RUNTIME_DIR", "jupyter_runtime"),
]:
    (ROOT / ".cache" / folder).mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(key, str(ROOT / ".cache" / folder))


def main():
    project = "regime_model"
    title = {
        "project_Asset_Allocation": "Does portfolio construction earn its complexity?",
        "regime_model": "Do market states improve next-session risk forecasts?",
        "project_FICC_Quant": "Curves, conventions and the limits of a one-swap hedge",
    }[project]
    nb = nbformat.v4.new_notebook()
    nb.metadata.kernelspec = {"name": "python3", "display_name": "Python 3", "language": "python"}
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md(
            "# "
            + title
            + "\n\n## Summary\n\n"
            + (ROOT / "docs/02-results.md").read_text().split("\n\n")[1]
        ),
        md(
            "## Context and methods\n\n"
            + (ROOT / "docs/01-methods.md")
            .read_text()
            .replace("../research/", "research/")
            .replace("(02-results.md)", "(docs/02-results.md)")
        ),
        md(
            "### Recompute from pinned inputs\n\nRuns the maintained pipeline, reusing matching checkpoints where available. No notebook-only model logic."
        ),
        code(
            "from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Markdown, Image\nfrom research.run_study import main\nfrom research.common import ROOT, RESULTS, FIGURES\nmain()"
        ),
        md(
            "## Data\n\nInput provenance records the exact vintage or the explicitly illustrative fixture. Retrieval dates do not imply historical availability."
        ),
        code(
            'manifest = json.loads((ROOT / "research/data/input_manifest.json").read_text())\ndisplay(Markdown("Input kind: **" + manifest.get("kind", "observed adjusted-close snapshots") + "**"))\nsources = pd.DataFrame(manifest.get("snapshots", manifest.get("inputs", [])))\ncolumns = [c for c in ["ticker", "rows", "first_date", "last_date", "path"] if c in sources]\ndisplay(sources[columns].head(10))'
        ),
        md("## Results"),
        code(
            'import re\ntext = (ROOT / "docs/02-results.md").read_text()\ntext = re.sub(r"!\\[[^\\]]*\\]\\([^)]*\\)", "", text)\ndisplay(Markdown(text.replace("../research/", "research/").replace("(01-methods.md)", "(docs/01-methods.md)")))'
        ),
    ]
    tables = {
        "project_Asset_Allocation": [
            "performance",
            "paired_intervals",
            "implementation",
            "cost_headroom",
        ],
        "regime_model": ["forecast_metrics", "diagnostics", "overlay_performance"],
        "project_FICC_Quant": [
            "valuation",
            "calibration",
            "convention_effects",
            "quote_buckets",
            "scenario_pnl",
            "fx_parity",
        ],
    }[project]
    figures = {
        "project_Asset_Allocation": ["wealth", "drawdown", "exposures", "incremental"],
        "regime_model": ["states", "forecast_comparison", "revisions", "overlay", "segmentation"],
        "project_FICC_Quant": ["curves", "calibration", "risk", "hedge"],
    }[project]
    for table in tables:
        cells += [
            md("### " + table.replace("_", " ").capitalize()),
            code(f'display(pd.read_csv(RESULTS / "{table}.csv").round(6).head(30))'),
        ]
    for fig in figures:
        cells += [
            md("### " + fig.replace("_", " ").capitalize()),
            code(f'display(Image(filename=str(FIGURES / "{fig}.png")))'),
        ]
    cells += [
        md(
            "## Calculation appendix\n\nIndependently reconstruct headline values and accounting identities from saved underlying outputs, then verify source/code/artifact hashes."
        ),
        code("from research.check_artifacts import independent_checks\nindependent_checks()"),
        md(
            "## Takeaways and next experiment\n\n"
            + (ROOT / "research/RESEARCH_AGENDA.md").read_text()
        ),
        md(
            "See [source register](research/SOURCES.md), [audit](research/AUDIT.md), [protocol](research/PROTOCOL.md) and [publication review](PUBLICATION.md). No live publication is part of this build."
        ),
    ]
    nb.cells = cells
    client = NotebookClient(
        nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}
    )
    client.execute()
    nb.cells[0] = md(
        "# "
        + title
        + "\n\n## Summary\n\n"
        + (ROOT / "docs/02-results.md").read_text().split("\n\n")[1]
    )
    nbformat.validate(nb)
    temp = ROOT / "study.ipynb.partial"
    nbformat.write(nb, temp)
    temp.replace(ROOT / "study.ipynb")
    html, _ = HTMLExporter().from_notebook_node(nb)
    dest = ROOT / "research/preview"
    dest.mkdir(exist_ok=True)
    (dest / "study.html").write_text(html)
    print("Saved executed study.ipynb and research/preview/study.html")


if __name__ == "__main__":
    main()
