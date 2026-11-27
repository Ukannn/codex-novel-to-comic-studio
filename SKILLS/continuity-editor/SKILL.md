---
name: continuity-editor
description: Review generated chapter images against visual bible references and produce a QC report.
---

# Continuity Editor

Read `config/user-preferences.json` and a chapter's `director-briefs/`, `finished-pages/`, optional fallback `page-art/`, `storyboard.json`, and `visual-bible/`.

Produce `chapters/chNN/qc-report.json` with:

- overall notes
- page-level and panel-level issues
- source span, character card, setting card, or style rule involved
- suggested action: `accept`, `edit`, or `regenerate`
- edit instruction when a local fix is enough

In v0, do not pretend to have a precise numeric vision model score. Use qualitative severity: `low`, `medium`, `high`, `blocking`.

Review four layers: story faithfulness, continuity, image quality, and comic readability. A chapter cannot be marked approved while `high` or `blocking` issues remain open.

For finished-page image2 output, also check exact rendered text in `project.target_language`, balloon order, SFX placement, and whether the generated page obeyed the director brief's panel geometry instead of collapsing into a mechanical grid or poster collage.

Run basic image QC with `TOOLS/qc_chapter.py --preferences config/user-preferences.json`
and the chapter's storyboard, finished-pages directory and report path. Supply
`--page-art` only when checking a separate fallback art layer. Tool QC covers
file/image checks; the four editorial review layers above still need review.
