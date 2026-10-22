# Windows and local-only reconstruction

Use the Windows sections for local setup/rendering on Windows. Use the **local-only route** only when the user requires local processing or has chosen it after an external-call restriction. This is an alternative workflow, not a claim that the stock external-image validator accepts local artwork.

## Working CLI before installation

`editppt` missing from PATH does not imply missing code or dependencies. Try the installed skill entry point with an available Python:

```powershell
$skillRoot = '<absolute skill directory>'
$cli = Join-Path $skillRoot 'cli\editppt\cli.py'
python $cli --help
python $cli doctor
```

Use the bundled workspace Python if the system interpreter lacks dependencies. If dependencies truly are absent, install into a task-local environment using an available package manager. Do not repeat `uv` access-denied errors or a stalled network install under unchanged conditions. A working direct entry point needs no reinstall, global PATH edit, or `setup` mutation. Pass this verified invocation to every worker.

## Mixed PPTX and near-full-slide images

Preflight the ZIP/XML without editing it: page count/order, native text, picture placements, original media dimensions, and notes. The lightweight extractor has a strict full-slide position check; offsets or an existing native title can cause its rejection. Use a local render, not a modified source deck, for composition/coordinates:

```powershell
& "$skillRoot\scripts\windows-pptx-render.ps1" -InputPath '<original.pptx>' -PdfPath '<work/source.pdf>'
```

The helper opens the presentation read-only without a visible presentation window, uses `SaveAs(..., 32)` for PDF, closes only its own deck, and quits the application only if no presentations remain. COM may fail inside the Windows sandbox with `80070520` even when PowerPoint is installed. Request the normal runtime permission for this **local** operation and retry there; this is not permission for uploads. `ExportAsFixedFormat` can fail PowerShell parameter binding, so the helper uses the verified `SaveAs` route.

If no usable PowerPoint COM exists, use an available supported renderer. Do not install Office/LibreOffice as a side effect. In the Codex desktop artifact environment, use bundled LibreOffice only when that environment requires it; discover its path rather than guessing a user installation.

Keep the original PPTX and media. For unclear labels or detailed scientific plots, inspect the original embedded raster (often substantially larger than the rendered page). Map high-resolution asset coordinates back to the page canvas; do not change `page_request.json` dimensions to fit one crop. Keep a note of rendered-to-original scale and placement/cropping transforms.

## Local-only preparation and OCR

Do not expose or delete stored credentials. Override their lookup only in the command process using an **empty workspace config directory**, and clear the process token. Do this in each new shell session that invokes hints:

```powershell
$env:HOME = $env:USERPROFILE
$env:EDITPPT_CONFIG_HOME = '<absolute work/empty-offline-config>'
$env:PADDLE_OCR_TOKEN = ''
python $cli prepare '<input image/PDF/PPTX>' --job-dir '<absolute run>' --no-text-hints
python $cli run hints '<absolute run>'
```

Ensure the selected config directory contains no inherited `config.yaml`. `--no-text-hints` makes preparation itself avoid OCR calls; the second command produces local geometry hints under the isolated environment. A backend contract may still be written into the request by the current CLI. In local-only mode it is inactive: do not execute it or infer upload authorization from it. There is no current `editppt --local-only` flag.

Windows OCR can supply recognized text without an external service:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$skillRoot\scripts\windows-local-ocr.ps1" -InputDir '<absolute run/pages>' -OutputDir '<absolute work/local-ocr>' -Language 'zh-Hans-CN'
```

Use Windows PowerShell for WinRT interop. The helper checks the installed language, writes UTF-8 JSON per page, and records image dimensions and word boxes. Read files with `utf-8-sig` to handle Windows PowerShell's BOM. Missing language packs are an environment limitation, not a reason to upload or install packages automatically. If image dimensions exceed the OCR engine limit, create an OCR-only reduced copy and retain its scale; never overwrite the reconstruction source. Geometry hints and Windows OCR remain supplementary evidence; inspect the image to correct recognition errors and avoid guessing unclear text.

## Local object-source decisions

These rules supersede the standard decision tree's mandatory external-image steps in local-only mode:

1. Rebuild ordinary text, layout, tables, axes, chart labels, simple diagrams and connectors as native objects. Preserve real wording, values and source geometry.
2. Extract exact photos, logos, icons, screenshots, and irrecoverable data-plot regions locally as independent image assets. `source_type: user-provided` is truthful for assets derived from the user's source. Record the source path, crop/transform or cleanup method, and remaining raster content. Do not use `imagegen` or `asset-sheet-separated` for a local crop.
3. Remove baked text that will be rebuilt natively. Small local masks/inpainting/interpolation are acceptable when source identity remains intact; inspect the clean base and final composite. Use native fills for simple backgrounds. Do not hallucinate missing evidence, cover old text with duplicate editable copies, or split a full source into tiles to evade validation.
4. For an unreadable label, inspect higher-resolution embedded media. If still unclear, preserve only that small region and disclose it. Do not invent missing chart data. Separate plot labels where feasible while retaining the exact data trace.
5. Prefer native text with sub/superscript runs and fraction lines for simple formulas. If the supplied TeX tool fails for a real environment reason, use a verified local renderer such as already-installed MathText. Preserve the formula source, actual renderer, and `latex-rendered-formula` provenance; disclose the rendered formula's lack of text editability. Do not repeatedly invoke broken MiKTeX or install global TeX.

Partial raster content is an editability limitation, not a package failure. A whole source slide underneath editable text remains prohibited. A genuinely cleaned photographic background is permissible only when removal is recorded and visually checked; image dimensions alone cannot establish that the lettering is gone.

## Worker mode and ownership

Generate prompts with `--processing-mode local-only`. The builder prints no stock dispatch command for that route. Assign actual workers and track page ownership/progress separately; reuse idle workers one page at a time. Standard runtime `page_jobs.json` remains the preparation record, not a fabricated completion ledger. Parent reconstruction is permitted sequentially if no workers are available.

Each worker still follows the manifest coordinate schema, builds via the CLI, writes `validation.json` with an **absolute** `--report`, checks exact file existence, and retains actual stock policy failures. `imagegen-jobs.json` may remain empty. Do not fix a source-policy failure by changing provenance or a boolean. Do not return nonexistent report paths.

## Local assembly and honest validation

```powershell
$env:HOME = $env:USERPROFILE
python "$skillRoot\scripts\assemble-local-deck.py" --run '<absolute run>' --out '<deliverable.pptx>' --allow-local-assets --notes-from '<original.pptx>'
```

Omit `--notes-from` for inputs without an original PPTX. For a PPTX normalized through PDF, always pass the original; it verifies source slide count and preserves notes text/page mapping. Notes formatting, embedded note media, animations and transitions are not reconstructed by this helper. In the standard route, the same **local assembly** helper can restore notes after PDF normalization if stock finalization cannot import the original notes; omit `--allow-local-assets` when no local-source exceptions are needed. Local assembly does not imply that all upstream processing was local.

The helper derives page count/order from the prepared deck rather than a hardcoded number. It:

- Requires all seven page artifacts and invokes the unchanged stock validator afresh, writing separate raw reports under `local-validation/`.
- Blocks missing text/assets/provenance, malformed coordinates, broken relationships, changed media, line/table defects, and package errors.
- With `--allow-local-assets`, accepts only the named external-source policy conflicts for images with linked, truthful `user-provided` provenance. It rejects unknown violations and missing image links.
- For a cleaned full-slide photographic base, also requires recorded foreground removal, comparison evidence, and a background check; identical original source pixels remain a failure even after renaming/re-encoding. Visual inspection is still required to assess cleanup quality.
- Builds from page manifests, checks final slide count/order/editable text and all relationship targets, and verifies notes content. It writes the deliverable only after these checks.
- Writes `local-validation/local-assembly-validation.json`, preserving stock `passed:false` values and listing policy exceptions. It does not modify runtime validators, page reports, dispatch state, or finalization status.

The stock raw report and separate local report answer different questions. State which checks passed; never label a policy exception as an unqualified stock pass. A helper failure is a repair/blocker, not permission to add a broad exception filter.

## Rendering and delivery

For Chinese text, use an installed PowerPoint face such as `Microsoft YaHei` and set `text_boxes[].preview_font` to a verified local font file such as `C:/Windows/Fonts/msyh.ttc` (bold: `msyhbd.ttc`). The face name alone may not configure Pillow. Preserve Windows font paths as environment-specific choices, not universal assumptions.

Render an early representative page/deck locally to catch font fitting, glyph fallback, and line spacing. After assembly, use the PowerPoint helper to render the final deck, verify the expected page count, and inspect dense/changed pages. Fix specific clipping and re-render the repair; do not repeatedly export every accumulated prefix without a reason.

Report the final editable content and limits plainly: main text/shapes may be editable while photographs, dense plots, tiny uncertain labels, or some formulas remain separate images. Mention material background/font differences. Deliver only the requested output, keeping OCR, previews, scripts and validation reports in the working directory unless requested.
