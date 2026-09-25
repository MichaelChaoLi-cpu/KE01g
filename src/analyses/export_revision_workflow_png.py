"""Rasterize the SVG review drafts without thumbnail cropping.

Run after render_revision_workflow_previews.mjs, with CairoSVG available.
On macOS: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python <script>
"""
from pathlib import Path
import cairosvg

folder = Path(__file__).resolve().parents[2] / 'data/exp/revision-comment-4'
for name in ('Figure_methodological_flowchart_review', 'Graphical_abstract_review'):
    cairosvg.svg2png(url=str(folder / f'{name}.svg'),
                    write_to=str(folder / f'{name}.png'), output_width=2656)
