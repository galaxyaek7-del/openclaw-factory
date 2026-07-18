"""Single-artifact packaging (Universal Production Engine §3/§6,
2026-07-18). Every family shipped so far (kdp_books/professional_
templates/digital_toolkits/knowledge_bases/automation_systems) already
produces exactly ONE distributable file (a PDF) via its Asset Generation
stage — Packaging is a real, honest no-op passthrough for these, not a
fabricated bundling step. A future multi-file family (e.g.
spreadsheet_systems shipping a workbook + a setup guide) registers a
real zip-bundling packager here under its own name — this module is
never touched to add one.
"""

from . import registry


class SingleFilePackager:
    """Passthrough for any family whose Asset Generation stage already
    produces exactly one distributable file."""
    name = "single_file"

    def package(self, spec, generation_result):
        """generation_result: the real Asset Generation build() result
        (has "path" — the single produced file). Returns that same path
        as the one distributable artifact — never copies, moves, or
        re-writes it."""
        path = generation_result.get("path")
        return {
            "artifact_path": path,
            "method": "single_file",
            "file_count": 1 if path else 0,
        }


registry.register(SingleFilePackager())
