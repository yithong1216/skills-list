# Page Reconstructor Prompt Template

Placeholders of the form `{{NAME}}` are filled by `scripts/build-page-worker-prompt.py`.

```text
Rebuild one page for image-to-editable-ppt.

Run dir: {{RUN_DIR}}
Page id: {{PAGE_ID}}
Page dir: {{PAGE_DIR}}
Source image: {{SOURCE_IMAGE}}
Processing mode: {{PROCESSING_MODE}}

If processing mode is local-only, first read {{SKILL_ROOT}}/references/windows-local-workflow.md. Its local object-source and validation rules replace the external-image-only rules below. No OCR/image endpoint calls, no generated provenance for local crops, no stock dispatch wait. The parent's local assignment establishes ownership. Keep actual raw validation failures; offline assembly handles only explicitly documented local-source exceptions.

You own only this Page dir. Do not edit deck_manifest.json, page_jobs.json, notes_manifest.json, final outputs, the original input, or any other page directory.

Read references by task, before acting on their rules. All reference paths below are under {{SKILL_ROOT}}/references/; do not reread unchanged sections already available in this execution.
- Start with page_request.json and page-decision-tree.md's introduction, "Common Failure Mode: False Progress", and "Pre-Decision: Page Inventory". Inspect the source and build the inventory, then read sections 1 and 2 for object-source decisions.
- Before native reconstruction, read section 3.1 for text; read sections 3.2-3.6 when the inventory contains their formulas, structural objects/tables, corners, decorated text, or groups. Read "Final Self-Check" and "Fix versus Warning" before acceptance or a repair decision.
- Read manifest-schema.md's page_request.json and pages/page_NNN/manifest.json contracts before writing the manifest, loading applicable object contracts such as "Native tables". Before image jobs read the image_backend and imagegen-jobs.json contracts; for region splitting read "Asset sheet regions and split reports". Before returning read the validation.json and page_result.json contracts. Deck-state and notes contracts are outside your ownership.
- Use cli-helper.md for the commands needed now: "Page Build Commands", and "Image Backend Commands", "Asset Processing Commands", or "Formula Commands" when applicable. Do not load unrelated install or orchestration instructions.

Hard rules (reminders; authoritative details remain in the references):
1. Standard mode: separate foreground visuals through the selected image backend; its fallback rules do not permit crops. Local-only mode: preserve exact local artwork under windows-local-workflow.md with truthful user-provided provenance. In either mode, never invent missing evidence or duplicate baked text.
2. Decide background, then foreground, then native elements; consume text hints only after steps 1-2 decisions — page-decision-tree.md introduction and section 3.1.
3. Build from manifest.json with the deterministic runtime; preserve source-pixel geometry and request canvas — manifest-schema.md's page_request.json and manifest.json contracts.
4. Standard mode: execute the recorded backend contract, built-in first with actual result import and permitted fallback events. Local-only mode: the recorded external contract is inactive; no endpoint calls. Keep imagegen-jobs empty when no image backend was used.
5. Structural validation never proves visual fidelity. Apply the chosen mode's object-source rules and keep its actual validation evidence.

Recovery: read any previous validation failure before editing. Verify reusable artifacts against the current source, page request/backend contract, manifest links, and imagegen-jobs.json provenance (paths/hashes); inspect their visual content where relevant. Reuse compliant artifacts and repair only failed or dependent parts. Rebuild from the inventory only when the source or object-source decisions are invalid. Never flip leftover validation to passed or return stale outputs without validating the current artifact set.

Execution:
1. Record the inventory and background/foreground decisions, then execute necessary image jobs under page-decision-tree.md sections 1-2. Page-local image jobs remain serial. Import and process selected image outputs using the image-job contract.
2. Reconstruct native elements under the applicable section 3 rules and write manifest.json using its field contract.
3. Run `editppt page build "{{PAGE_DIR}}"`, then `editppt page contact-sheet "{{PAGE_DIR}}"`.
4. Perform the Final Self-Check against the source and run `editppt page validate "{{PAGE_DIR}}" --report "{{PAGE_DIR}}/validation.json"`. Use the parent's verified Python CLI entry point if the launcher is unavailable. Parse the saved file, not just stdout. Fix actual page-local issues; after a change rebuild and verify the changed result. In local-only mode preserve source-policy failures truthfully and distinguish them from structural failures.
5. Verify every required artifact exists at the exact absolute path you return. Do not claim a report was saved when validate only printed JSON, and do not return a relative report path nested beneath the page a second time. On Windows, use an existing CJK preview_font file as well as a real installed PowerPoint font face.

Required outputs: manifest.json, imagegen-jobs.json, page.pptx, preview.png, split_assets_contact.png, validation.json, page_result.json. Validation and page-result shapes are owned by manifest-schema.md. Standard recording requires top-level `passed: true`; local-only handoff retains the actual raw result, identifies source-policy exceptions, and still requires all artifacts and no real structural/text defects.

Routine repairs and recorded backend fallbacks require no extra user confirmation. Respect runtime-required approvals; the parent owns the OCR confirmation exception. Do not retry the same failing tool with unchanged inputs and conditions. If a hard requirement remains blocked after applicable fallbacks, write validation.json with `passed: false` and the concrete cause/error, plus page_result.json referencing only artifacts that exist. Preserve progress; do not fabricate outputs, substitute an approximate page, or request an unconditional fresh reconstruction.

Return only verified available artifact paths (omit missing artifacts on failure), plus editable-object counts, actual validation status/reasons, and material raster/visual limitations:
page_manifest=`<absolute path>`
page_pptx=`<absolute path>`
preview=`<absolute path>`
contact_sheet=`<absolute path>`
validation=`<absolute path>`
page_result=`<absolute path>`
```
