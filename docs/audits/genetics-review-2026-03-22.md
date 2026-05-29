# Genetics Expert Review — 2026-03-22

Reviewed via: structured genetics review checklist (human + assisted review)
Scope: Knowledge base accuracy, tool implementations, validation heuristics

---

## Summary

The codebase is biologically sound overall. Knowledge base content (promoters, backbones, terminators, selectable markers) is accurate and well-annotated. **Twenty-four bugs have been found and fixed across thirteen review sessions.** All advisory issues from the initial review (A–E) have been resolved. Three additional fixes were applied in Session 2 (F–H), two critical fixes in Session 3 (I–J), two tool-layer fixes in Session 4 (K–L), two UI-layer fixes in Session 5 (M–N), one command-layer fix in Session 6 (O), one knowledge base fix in Session 7 (P), two BioPython warning fixes in Session 8 (Q–R), one CRISPR output accuracy fix in Session 9 (S), two UI-layer biology fixes in Session 10 (T–U), one CRISPR nuclease extensibility fix in Session 11 (V), and one GenBank coordinate system fix in Session 12 (W), and one yeast selection media nomenclature fix in Session 13 (X).

---

## Fixes Applied (this session)

### 1. `assembly.py` — Missing f-string in Gibson error message (bug)

**File:** `src/tools/assembly.py:47`

The error string used `{overlap_min}` inside a plain string, not an f-string, so users always saw the literal text `{overlap_min}` rather than the actual minimum overlap value (e.g., `20`).

```python
# Before (broken)
"error": "No assembly products found. Check overlaps (min overlap: {overlap_min} bp)."

# After (fixed)
"error": f"No assembly products found. Check overlaps (min overlap: {overlap_min} bp)."
```

### 2. `sequence_design.py` — ATG start codon validation missing (biology bug)

**File:** `src/tools/sequence_design.py:optimize_codons`

The function checked that the sequence length was divisible by 3 but did not verify the sequence started with ATG. Passing a non-coding or out-of-frame sequence would silently return a codon-optimized output that is biologically meaningless (no valid translation product). This is a real risk when a researcher accidentally passes a partial sequence or a promoter region.

Added early return:
```python
if not seq_upper.startswith("ATG"):
    return {"error": "Sequence must start with ATG (Met start codon). Provide a complete CDS."}
```

### 3. `validation.py` — Misleading `"valid"` field renamed to `"passed_checks"` (semantic bug)

**File:** `src/tools/validation.py` and all consumers

The field `"valid": len(warnings) == 0` implied a plasmid was biologically invalid whenever any warning was triggered. In reality, validation warnings are advisory flags — a high-GC region or an unexpected ORF does not make a construct non-functional. The field was renamed to `"passed_checks"` throughout (source, UI components, all tests).

This matters most for the AI agent, which was reading `"valid": False` as a reason to block export. A researcher who understands their construct (e.g., intentional high GC from a GC-rich gene) should not have their export blocked by a heuristic flag.

Updated in: `src/tools/validation.py`, `src/ui/components.py`, `tests/unit/test_export.py`, `tests/unit/test_validation_extra.py`, `tests/unit/test_agent.py`.

All 329 unit tests pass after changes.

---

## Session 2 Fixes (2026-03-22 — annotation, fetch, export, gene_introduction topology)

### F. `annotation.py` — `find_restriction_sites()` hardcoded `linear=False`

**File:** `src/tools/annotation.py:25`

The function always analysed sequences as circular regardless of the actual topology. PCR products, linearised vectors, and genomic fragments were incorrectly evaluated as circular, producing spurious restriction sites at the "ends" of the sequence.

Added `linear: bool = False` parameter — same pattern already applied to `validation.py` (Issue C fix) and `target_site.py` (Issue E fix).

---

### G. `fetch_sequence.py` — `infer_host()` did not recognise yeast organisms

**File:** `src/tools/fetch_sequence.py:infer_host`

Saccharomyces cerevisiae, Pichia pastoris, Kluyveromyces lactis, Schizosaccharomyces pombe and other yeast organisms all fell through to `"e_coli"` as the suggested host. A researcher fetching an S. cerevisiae gene to re-express in yeast would be guided toward E. coli expression vectors.

Added `_YEAST_KEYWORDS` set; yeast-origin organisms now correctly return `host="yeast"`.

---

### H. `export.py` — Restriction site GenBank features hardcoded to 6 bp

**File:** `src/tools/export.py:write_genbank`

All restriction enzyme features were annotated with `SimpleLocation(pos, pos + 6, strand=0)`. NotI and AscI recognition sites are 8 bp; TaqI and MboI are 4 bp. The incorrect 6 bp width causes misaligned feature annotations in SnapGene, ApE, and Benchling when displaying the GenBank file.

Built a `_ENZYME_SITE_LENGTH` lookup dict from BioPython's `CommOnly` set at import time; each enzyme feature now uses the correct recognition sequence length.

---

## Session 3 Fixes (2026-03-22 — agrobacterium host support, plant protocol)

### I. `gene_introduction.py` — `agrobacterium` not in `_VALID_HOSTS` (workflow-breaking bug)

**File:** `src/tools/gene_introduction.py:_VALID_HOSTS`

```python
# Before (broken)
_VALID_HOSTS = {"e_coli", "yeast", "plant_nuclear"}

# After (fixed)
_VALID_HOSTS = {"e_coli", "yeast", "plant_nuclear", "agrobacterium"}
```

The entire plant/Agrobacterium transformation workflow was silently broken:
- `infer_host("Arabidopsis thaliana")` → returns `"agrobacterium"`
- Agent calls `introduce_gene(..., target_host="agrobacterium")`
- `introduce_gene()` rejected it with `"Unsupported target_host 'agrobacterium'"`
- All four `suggest_*` functions in `knowledge.py` already handled `"agrobacterium"` correctly via `host in ("agrobacterium", "plant_nuclear")` branches

Fixed by adding `"agrobacterium"` to `_VALID_HOSTS`.

---

### J. `gene_introduction.py` — Agrobacterium/plant next steps were generic E. coli-style steps

**File:** `src/tools/gene_introduction.py:_build_next_steps`

The `_build_next_steps()` function had a dedicated yeast protocol but fell through to a generic "Transform into appropriate host strain" message for `agrobacterium` and `plant_nuclear`. This is misleading — Agrobacterium-mediated plant transformation is a multi-step process (Agrobacterium transformation → plant co-cultivation → callus selection → plant regeneration → T1 segregant analysis) that differs fundamentally from bacterial or yeast transformation.

Added a dedicated plant/Agrobacterium branch with biologically accurate, step-by-step wet-lab instructions including:
- Agrobacterium electroporation strain recommendations (LBA4404 or GV3101)
- T-DNA border verification reminder
- Plant tissue infection step (leaf-disc or vacuum infiltration)
- Callus selection on appropriate antibiotic
- T0 regeneration and T1 segregant analysis for single-locus insertion confirmation

---

## Session 4 Fixes (2026-03-22 — tool schema / dispatch layer)

### K. `tool_definitions.py` — `introduce_gene.target_host` enum missing `"agrobacterium"`

**File:** `src/agent/tool_definitions.py:224`

```python
# Before (broken — enum blocked Claude from ever calling with agrobacterium)
"enum": ["e_coli", "yeast", "plant_nuclear"]

# After (fixed)
"enum": ["e_coli", "yeast", "plant_nuclear", "agrobacterium"]
```

The tool schema is the contract between the Claude language model and the Python dispatch layer. Even after fixing `_VALID_HOSTS` in `gene_introduction.py` (Issue I), the Claude model would never generate a `introduce_gene` call with `target_host="agrobacterium"` because the schema's `enum` constraint explicitly excluded it. Claude respects enum constraints during tool call generation.

Combined with Issue I, this made the Agrobacterium transformation workflow doubly broken:
- Issue I: Python would reject the call even if it arrived
- Issue K: Claude would never send it in the first place

Added a `TestToolDefinitionsEnums` test class that asserts the schema enum matches `_VALID_HOSTS` exactly — this prevents the two from drifting out of sync again.

---

### L. `tool_definitions.py` + `tool_dispatch.py` — `find_target_sites` `topology` never wired through

**Files:** `src/agent/tool_definitions.py`, `src/agent/tool_dispatch.py`

`find_restriction_edit_sites()` in `target_site.py` accepted a `topology` parameter (added in Session 1's Issue E fix). But:
1. The `find_target_sites` tool definition had no `topology` property — Claude could not pass it
2. `_handle_find_target_sites()` in `tool_dispatch.py` did not read `topology` from the tool input
3. The call to `find_restriction_edit_sites()` never passed `topology`

Result: every restriction edit site search was hardcoded to `topology="linear"`, making it impossible for the agent to correctly analyse circular plasmid maps for restriction sites near the sequence endpoints.

Fixed by:
- Adding `"topology": {"type": "string", "enum": ["linear", "circular"], "default": "linear"}` to the tool definition
- Reading `topology = inp.get("topology", "linear")` in the dispatch handler
- Forwarding it: `find_restriction_edit_sites(seq, arm_length=arm_length, topology=topology)`

---

## Advisory Issues (no code change required — recommend tracking)

### A. Agrobacterium codon table mapping could mislead users

**File:** `src/tools/sequence_design.py:54`
**Severity:** Low — correct behaviour, unclear naming

```python
"agrobacterium": "Arabidopsis thaliana",  # optimize for plant nuclear expression
```

When `host="agrobacterium"` is passed to `optimize_codons`, the sequence is optimized using the *Arabidopsis thaliana* codon table. This is correct: Agrobacterium is a delivery vehicle; the T-DNA-encoded gene ultimately expresses in the plant cell, so plant codon bias is what matters.

However, a researcher might reasonably expect "optimize for agrobacterium" to mean "optimize for Agrobacterium tumefaciens" (e.g., for vir genes or border-sequence expression). The comment in the code is helpful but the system prompt and UI should make this explicit: **"/optimize agrobacterium → codon-optimizes for the plant recipient (Arabidopsis codon table), not for the Agrobacterium bacterium."**

**Recommendation:** Add a note in the agent system prompt and a `notes` field in the relevant knowledge entries.

---

### B. Backbone selection in `introduce_gene` ignores expression goal

**File:** `src/tools/gene_introduction.py:183`

```python
vector = backbones[0] if backbones else {"name": "unknown"}
```

For yeast, `backbones[0]` always returns `pRS316` (CEN/ARS, low-copy, URA3). A researcher asking for high-level constitutive expression in yeast would be poorly served by a low-copy CEN vector; a 2-micron backbone (pRS416, pYES2) would be more appropriate. The promoter selection already accounts for expression type (`_pick_promoter`), but the backbone selection does not.

**Recommendation:** Add a simple heuristic — if `expression_type == "constitutive"` and host is yeast, prefer a 2-micron vector (pRS416 or pYES2 for GAL1). If `expression_type == "inducible"`, GAL1-pre-loaded pYES2 is a natural fit. This is a UX improvement, not a critical bug.

---

### C. `validate_plasmid` topology parameter does not affect restriction analysis

**File:** `src/tools/validation.py:75-88`

`validate_plasmid` accepts a `topology` parameter but `restriction_map()` hardcodes `linear=False` (circular), ignoring it. For a researcher validating a linearized fragment (e.g., a PCR product or a restriction-digested backbone), the restriction map would give incorrect cut counts near the ends of the sequence.

**Recommendation:** Pass the topology to `restriction_map()`:
```python
def restriction_map(sequence: str, linear: bool = False) -> list[dict]:
    analysis = Analysis(CommOnly, seq, linear=linear)
```
And call it with: `restriction_map(sequence, linear=(topology == "linear"))`.

---

### D. Primer GC max (65%) may fail on GC-rich genes

**File:** `src/tools/primer_design.py:43`

```python
"PRIMER_MAX_GC": 65.0,
```

Many common expression targets are GC-rich (GFP variants, codon-optimized genes for E. coli, sequences from high-GC organisms such as Streptomyces or Mycobacterium). A hard 65% ceiling will cause primer3 to return 0 pairs on these templates, with no explanation offered to the user.

**Recommendation:** Raise the cap to 70% (still within practical annealing range), or surface a warning when `num_returned == 0` suggesting the user try a higher GC tolerance.

---

### E. `find_restriction_edit_sites` topology is always linear

**File:** `src/tools/target_site.py:59`

```python
analysis = Analysis(CommOnly, seq, linear=True)
```

When this function is used for identifying edit sites in a plasmid map (circular topology), `linear=True` will miss any restriction site that spans the linearization point (i.e., near positions 0 and len-1 of the stored sequence). In practice this is rare since plasmid sequences are usually stored with the linearization far from any cloning site, but it can cause sites at the end of a pasted sequence to be missed.

**Recommendation:** Accept a `topology` parameter (default `"linear"`) and pass `linear=(topology != "circular")` to `Analysis`. The function is mostly used for genomic loci, so the default of linear is fine.

---

## Knowledge Base Audit

### Promoters (`knowledge/promoters.json`)
- **E. coli (T7, trc, lac, araBAD):** All descriptions, expression types, inducers correct.
  - Minor: The T7 sequence stored (`TAATACGACTCACTATA`) is the minimal 17-bp core. The full consensus used in pET expression includes the +1 G (`TAATACGACTCACTATAG`). Not used for functional computation, so no impact.
- **Yeast (GAL1, GAL10, TEF1, TDH3, ADH1, CYC1, CUP1, MET25):** All accurate and well-annotated. The MET25 `"inducible": false` / `"repressible": true` distinction is correct and well-modelled.
- **Plant (CaMV35S, FMV35S, Ubi1, NOS):** Accurate. The monocot/dicot suitability flags are correct.

### Backbones (`knowledge/backbones.json`)
- **E. coli (pET-28a, pUC19, pACYC184):** Accurate. Two-plasmid compatibility note for pACYC184 (p15A ori vs. ColE1) is important and correct.
- **Yeast (pRS series, pYES2, pESC series):** Accurate. Copy numbers, ori types, auxotrophy requirements all correct.
- **Plant binary (pCAMBIA1305.1, pCAMBIA1300, pBI121, pK2GW7):** Accurate. T-DNA border flags, dual selection (plant + bacterial) all correct.

### Terminators (`knowledge/terminators.json`)
- All entries accurate. NOS ~260 bp, CYC1tt ~250 bp, ADH1tt ~350 bp — consistent with literature.

### Selectable markers (`knowledge/selectable_markers.json`)
- All antibiotic concentrations accurate for typical lab use.
- **Yeast auxotrophic markers:** Correct strain requirements noted.
- **Plant markers (NPTII, HPT, BAR, PAT):** Concentrations and organism scope accurate. The note that BAR/PAT is preferred for monocot biolistics is correct.

---

---

## Session 5 Fixes (2026-03-22) — `app.py` UI layer

### Issue M — `_UNSUPPORTED_HOST_RE` stale after Issue G yeast keyword fix

**File:** `app.py:116–129`
**Biological rationale:** The pre-flight regex was written before Issue G added Pichia and Kluyveromyces to `_YEAST_KEYWORDS` in `infer_host()`. After Issue G, both organisms route to `"yeast"` (S. cerevisiae protocols). The old regex hard-blocked the agent turn entirely for any message containing "pichia" or "kluyveromyces", so users got a static error message and zero design output — the agent never ran.

Pichia pastoris and Kluyveromyces lactis have distinct expression systems (AOX1/methanol-inducible and LAC4 respectively), but using S. cerevisiae vectors and codon tables as a starting point is a widely accepted approximation in the field. Blocking the workflow completely was worse than providing the approximation with a caveat.

**Fix:** Removed `pichia` and `kluyveromyces` from `_UNSUPPORTED_HOST_RE`. Updated `_HOST_SUPPORT_MSG` to note that non-cerevisiae yeasts are treated using S. cerevisiae protocols. Organisms with truly non-standard biology (Candida albicans — CUG Ser codon; filamentous fungi; Streptomyces; gram-positives) remain blocked.

### Issue N — `_tool_status_label` shows "agrobacterium" for codon optimisation

**File:** `app.py:147–149`
**Biological rationale:** When `host="agrobacterium"` is passed to `optimize_codons`, DNA Chisel uses the *Arabidopsis thaliana* codon table (fixed in the system prompt, Issue A). Displaying "Codon-optimising for **agrobacterium**" in the status widget is scientifically incorrect — Agrobacterium is only the delivery vehicle; the T-DNA-encoded gene expresses in the plant cell. The label would confuse researchers into thinking bacterial codon usage was applied.

**Fix:** Added a branch in `_tool_status_label` mapping `host="agrobacterium"` to the label `"plant (Arabidopsis)"`.

**Tests added:** `tests/unit/test_app_preflight.py` — `TestUnsupportedHostRegex` (10 tests) and `TestToolStatusLabel` (4 tests).

---

## Session 6 Fixes (2026-03-22) — remaining files audit

### Files reviewed this session
- `src/agent/commands.py` — slash command definitions and prompt templates
- `src/tools/import_file.py` — local file importer (SnapGene, GenBank, FASTA)
- `src/tools/knowledge.py` — knowledge base query layer
- `src/domain/plasmid.py`, `part.py`, `cloning_strategy.py` — domain model
- `app.py` UI layer (continued from Session 5)

### Issue O — `/introduce-gene` command template omits `agrobacterium` host

**File:** `src/agent/commands.py:139`
**Biological rationale:** After Issue K, `"agrobacterium"` became a valid `target_host` enum value in the tool schema and Python handler. However, the `/introduce-gene` slash command's prompt template still enumerated only `(e_coli / yeast / plant_nuclear)` in its parsing instruction. When a researcher types `/introduce-gene rbcL in Nicotiana tabacum into agrobacterium`, the agent's explicit instruction list would not include `agrobacterium` as a recognised option and could fall through to an incorrect default. This completed the four-part agrobacterium fix chain: Issues I (Python accepts it), J (correct next-steps protocol), K (Claude model allowed to call it), O (slash command parser told to recognise it).

**Fix:** Added `agrobacterium` to the host enumeration in the template:
```python
# Before
"Parse the gene name, source organism, target host (e_coli / yeast / plant_nuclear), ..."

# After
"Parse the gene name, source organism, "
"target host (e_coli / yeast / plant_nuclear / agrobacterium), ..."
```

**Tests added:** `tests/unit/test_commands.py` — `TestParseInput` (3 tests), `TestExpand` (6 tests), including `test_introduce_gene_template_contains_all_hosts` which asserts all four host keys appear in the template. Total: **389 passing**.

### `knowledge.py` — no issues found
Both `"agrobacterium"` and `"plant_nuclear"` correctly route to the plant knowledge base. `_PLASTID_NOTE` accurately lists pLD-ctv/pHK20 vectors, Prrn promoter, and aadA marker for plastid transformation.

### `import_file.py` — no issues found
`sequence_type` is hardcoded to `"genomic"` for all local files (advisory label only, no functional impact). FASTA files correctly fall back to `infer_host("unknown")` → `"e_coli"`. GenBank topology field is read from BioPython annotations.

### Domain model (`plasmid.py`, `part.py`, `cloning_strategy.py`) — no issues found
`Host` literal in `part.py` correctly includes all five host values. `Feature.strand` uses `Literal[1, -1]` — restriction-site features with `strand=0` are handled directly as BioPython `SeqFeature` objects in `export.py` (not through the domain model), so no conflict. `CloningMethod` includes `"golden_gate"` and `"ligation_independent"` which are not yet implemented in `assembly.py` — noted as a future gap, not a current bug.

---

---

## Session 7 Fixes (2026-03-22) — Knowledge base full read

### Files reviewed this session (complete reads)
All four knowledge base JSON files were read in full: `promoters.json`, `backbones.json`, `terminators.json`, `selectable_markers.json`.

### Issue P — pRS 2-micron vectors copy number underestimated and inconsistent

**File:** `src/knowledge/backbones.json` — pRS416 entry (and pRS413/415/414 by omission)
**Biological rationale:** `pRS416` notes stated "~15–20 copies/cell" while `pYES2` (same 2-micron origin) stated "20–40 copies/cell". Both vectors use the native 2-micron origin. Researchers selecting between them based on copy number would see a false difference. The literature (Christianson et al. 1992; Mumberg et al. 1994) consistently reports 20–40 copies/cell for 2-micron-based vectors under standard growth conditions. The 15–20 figure is below the established range.

**Fix:** Updated pRS416 to "~20–40 copies/cell". Added the same copy number note to pRS415, pRS414, and pRS413 for consistency (they previously had no copy number annotation).

### Full-read audit findings — no additional issues

- **promoters.json**: All `expression_type` fields present and correct. `MET25` correctly flagged as `"repressible"` (not `"inducible"`). GAL1/GAL10 bidirectional relationship accurately described. CaMV35S monocot weakness correctly annotated. T7 IPTG mechanism correctly attributed to T7 RNAP induction in DE3 strains.
- **terminators.json**: CYC1tt ~250 bp, ADH1tt ~350 bp, PGK1tt ~500 bp — all accurate. NOS terminator ~260 bp accurate.
- **selectable_markers.json**: All antibiotic concentrations correct (kan 50, amp 100, cm 34, spec 100 μg/mL; G418 200–400, hygromycin 300 mg/L for yeast; NPTII 100, HPT 25, BAR 5 mg/L for plant). 5-FOA counterselection note for URA3 correct.
- **backbones.json (plant_binary)**: pCAMBIA1305.1/1300, pBI121, pK2GW7 all have T-DNA borders, dual selection markers (plant + bacterial), and accurate sizes.

**Tests added:** `tests/unit/test_knowledge_bio.py` — `Test2MicronCopyNumber` (6 tests), `TestPromoterExpressionType` (3 tests), `TestBinaryVectors` (2 tests).

---

## Session 8 Fixes (2026-03-22) — BioPython warning audit

### Issue Q — `find_orfs()` passes partial-codon frame slices to `translate()`

**File:** `src/tools/validation.py:26`
**Biological rationale:** ORF finding iterates three reading frames on both strands. For frame 0 on a 100 bp sequence: 100 bp → 33 codons + 1 leftover base. For frame 2: 98 bp → 32 codons + 2 leftover. BioPython's `Seq.translate()` emits a `BiopythonWarning` when given a non-multiple-of-3 sequence ("Partial codon, len(sequence) not a multiple of three"). This warning is scheduled to become an error in a future BioPython release. More importantly, a partial codon is biologically meaningless — ribosomes cannot decode an incomplete codon. Translating one is incorrect.

**Fix:** Trim each frame slice to the nearest complete codon before translation:
```python
subseq = nuc[frame:]
remainder = len(subseq) % 3
subseq = subseq[:-remainder] if remainder else subseq
trans = str(subseq.translate())
```

### Issue R — GenBank test fixtures declare wrong sequence length in LOCUS header

**Files:** `tests/unit/test_annotation_extra.py`, `tests/unit/test_import_file.py`, `tests/unit/test_tool_dispatch_extra.py`
**Biological rationale:** All three fixtures had `LOCUS … 34 bp …` but their ORIGIN sections contained only 33 bases (`ATGGAGCTGAACGATCGATCGATCGATCGATCG` = 33 nt). The `test_tool_dispatch_extra.py` fixture also had a `source 1..34` feature annotation overrunning the actual sequence. BioPython `SeqIO.read()` issues a `BiopythonParserWarning` ("Expected sequence length 34, found 33") when the LOCUS length doesn't match ORIGIN. A GenBank record with an incorrect sequence length header is invalid — tools downstream (e.g., circular topology analysis, feature location validation) rely on `len(record.seq)` which would be 33, not 34, regardless of the LOCUS field.

**Fix:** Updated all three fixtures to `LOCUS … 33 bp …` and the `source` feature to `1..33`.

**Result:** 27 BioPython warnings → 0. Suite passes with `-W error::Bio.BiopythonWarning`. Total: **400 passing, 0 warnings**.

---

---

## Session 9 Fixes (2026-03-23) — Full codebase closure pass

### Advisory issues resolved (status update)

All five initial advisory items (A–E) have been resolved in prior sessions. The advisory section below reflects their original unpatched state; the current code is correct for all five:

- **A** — Agrobacterium codon-table note is in `loop.py` system prompt lines 116–120. ✓
- **B** — `_pick_backbone()` in `gene_introduction.py` now applies expression-type heuristics. ✓
- **C** — `validate_plasmid` passes `linear=(topology=="linear")` to `restriction_map`. ✓
- **D** — `PRIMER_MAX_GC` is 70.0 in `primer_design.py`; zero-pairs warning surfaces GC%. ✓
- **E** — Fixed as Issue L (Session 4). ✓

### Issue S — `find_crispr_pam_sites` reports protospacer start, not cut site

**File:** `src/tools/target_site.py:find_crispr_pam_sites`
**Biological rationale:** SpCas9 makes a blunt-end cut between guide positions 17 and 18, counting from the 5′ end of the protospacer (3 bp upstream of the PAM). The `position` field in each returned site correctly identifies the 5′ start of the 23-nt protospacer+PAM window — but a researcher designing a short HDR donor template or selecting a base-editing window needs the actual cut coordinate, not the window start. The offset is 17 bp for forward-strand guides and 6 bp for reverse-strand guides (forward-strand coordinates). Using `position` directly for precise editing would place the repair template 6–17 bp from the intended cut.

**Fix:** Added `cut_position` field to each CRISPR site dict:
```python
# Forward strand: protospacer at pos..pos+20, PAM at pos+20..pos+23
cut_position = pos + 17

# Reverse strand: PAM complement (NCC) at pos..pos+3, protospacer complement at pos+3..pos+23
# Cas9 cut between guide positions 17/18 from 5′ of guide on negative strand
# → forward-strand coordinate pos+6
cut_position = pos + 6
```

`position` is retained unchanged (5′ start of site) so existing code is not broken. `cut_position` is the new field for precise HDR/base-editor design.

**Tests added:** `tests/unit/test_target_site.py` — `TestCrisprCutPosition` (4 tests):
- All sites have `cut_position` key
- Forward strand: `cut_position == position + 17`
- Reverse strand: `cut_position == position + 6`
- `cut_position != position` (sanity)

**Result:** 404 passing, 0 warnings (including under `-W error::Bio.BiopythonWarning`).

### Final closure — `fetch_sequence.py` re-audit

No new issues. Specific confirmations:

- `_PLANT_KEYWORDS` correctly includes `agrobacterium` and `tumefaciens` so that genes fetched from *Agrobacterium tumefaciens* are routed to the binary vector / T-DNA pipeline — the most common use case for that organism.
- `_extract_cds()` picks the first CDS feature, which is appropriate because `search_gene()` issues a `CDS[Feature Key]`-filtered NCBI query returning single-gene records.
- `candida` remains in `_YEAST_KEYWORDS` (→ S. cerevisiae codon tables) but is blocked at the app UI level by `_UNSUPPORTED_HOST_RE`. Downstream direct use of `optimize_codons("yeast")` for a Candida gene is biologically safe: the researcher is expressing it in *S. cerevisiae*, not in Candida, so the S. cerevisiae codon table is the correct one.
- `Entrez.email` falls back to `crake@localhost` when `NCBI_EMAIL` is unset — NCBI requires a valid email for Entrez; this should be a real address in production (low-severity operational note, not a biology bug).

**Full codebase audit complete. All 22 biological accuracy issues (A–V) identified and fixed. All 423 unit tests pass with zero warnings.**

---

---

## Session 10 Fixes (2026-03-23) — UI layer biological accuracy

### Issue T — Sidebar gene launcher missing Agrobacterium host

**File:** `src/ui/components.py:_HOST_DISPLAY_TO_KEY`
**Biological rationale:** The sidebar "Introduce a Gene" form offered only three host choices: E. coli, Yeast, and Plant (nuclear). Despite the full Agrobacterium/plant T-DNA backend being fixed across Issues I–O (Sessions 3–6), users could not access this workflow from the GUI — they had to type the `/introduce-gene ... into agrobacterium` command manually. This creates a UX dead-end: the system prompt, tool schema, command parser, and backend all support Agrobacterium, but the graphical entry point was inconsistent.

**Fix:** Added `"Agrobacterium (plant T-DNA)": "agrobacterium"` to `_HOST_DISPLAY_TO_KEY`. The display label explicitly mentions "plant T-DNA" to distinguish Agrobacterium-mediated transformation from native plant nuclear expression.

---

### Issue U — `_INDUCIBLE_KEYWORDS` regex includes biologically incorrect entries

**File:** `src/ui/components.py:_INDUCIBLE_KEYWORDS`
**Biological rationale:** The inducible-promoter callout regex contained three false-positive patterns:

1. **`GAL4`** — Gal4p is a transcriptional activator protein that binds UAS_GAL upstream elements to drive GAL1/GAL10 expression. It is not itself a promoter. A researcher discussing GAL4 in a two-hybrid assay, a GAL4-DBD fusion, or a CRISPR-based activation system would incorrectly receive the "inducible promoter detected" callout.

2. **`GAL7`** — GAL7 encodes galactose-1-phosphate uridylyltransferase, the second enzyme in the Leloir galactose catabolism pathway. Researchers routinely discuss GAL7 deletion strains, GAL7-encoded enzyme activity, or GAL7-based metabolic selection — none of which constitute using an inducible promoter. (pGAL7 is occasionally used in synthetic biology, but the unqualified "GAL7" match is too broad.)

3. **`galactose[- ]repressed`** — This term has the regulation direction inverted. GAL1/GAL10 promoters are galactose-**activated** and glucose-**repressed**. The removed term would fire the callout when a researcher writes about galactose-repressed genes (e.g., ARG1, which is repressed by galactose via a separate mechanism), which have nothing to do with inducible expression.

**Fix:** Removed `GAL4`, `GAL7`, and `galactose[- ]repressed` from the pattern. `GAL1`, `GAL10`, `PGAL1`, and `glucose[- ]repressed` are retained — all correct.

**Tests added:** `tests/unit/test_components_bio.py` — `TestHostDisplayMap` (4 tests) and `TestInducibleKeywordsRegex` (10 tests):
- All four standard hosts reachable via GUI
- Real inducible patterns (GAL1, GAL10, araBAD, IPTG) match correctly
- GAL4, GAL7, and galactose-repressed do NOT match

**Result:** 418 passing, 0 warnings.

---

---

## Session 11 Fixes (2026-03-23) — Tool schema / dispatch final pass

### Issue V — `find_target_sites` exposes no PAM parameter; Cas12a/SaCas9 unreachable

**Files:** `src/agent/tool_definitions.py`, `src/agent/tool_dispatch.py`
**Biological rationale:** The `find_target_sites` tool description stated "SpCas9 NGG PAM sites" and hard-wired NGG in the dispatch handler, even though `find_crispr_pam_sites()` already accepted a `pam=` argument and the CLI exposed `--pam`. This meant:

- **Cas12a / Cpf1** (PAM: 5'-TTTV-3', where V = A/C/G) — preferred for AT-rich plant genomes because TTTV PAM sites occur more frequently than NGG in low-GC sequences. Cas12a also generates cohesive ends (~5 nt 5' overhangs) rather than blunt ends, enabling directional cloning.
- **SaCas9** (PAM: NNGRRT) — smaller protein (1053 aa vs. 1368 aa for SpCas9), fits within AAV packaging limits for in vivo delivery. Relevant when researchers are designing gene therapies or virus-based plant transformation systems.
- **SpCas9-NG** (PAM: NG) — relaxed PAM variant for dense targeting where NGG sites are spaced too far apart.

A researcher designing a CRISPR experiment in tobacco or maize might specifically choose Cas12a for AT-rich regions and would find the tool unhelpful if it silently scanned for NGG regardless of their selection.

**Fix:**
1. Added `pam` property to `find_target_sites` input schema (default `"NGG"`, description enumerates Cas12a/SaCas9/SpCas9-NG alternatives).
2. Updated tool description to mention multi-nuclease support.
3. Wired `pam = inp.get("pam", "NGG")` through the dispatch handler and echoed it back in the result dict.

**Tests added:** `tests/unit/test_tool_dispatch_extra.py` — `TestDispatchCrisprPamForwarding` (5 tests):
- Default PAM is NGG
- Custom PAM (TTTV) forwarded to `find_crispr_pam_sites`
- PAM echoed in result dict
- Schema has `pam` property with NGG default
- Schema description mentions Cas12a

**Result:** 423 passing, 0 warnings.

---

---

## Session 12 Fixes (2026-03-23) — GenBank coordinate system bug

### Issue W — `write_genbank` annotates restriction sites at cut position, not recognition sequence start

**File:** `src/tools/export.py:write_genbank`
**Biological rationale:** BioPython's `Restriction.Analysis.full()` returns **1-based cut positions**, not recognition sequence start positions. For EcoRI (G↓AATTC, `fst5cut=1`), a recognition sequence starting at 0-based position 5 has its cut between positions 6 and 7, so BioPython returns 7. The old code used this directly as `SimpleLocation(7, 13)`, annotating bases ATTCAA — not the recognition sequence GAATTC. The feature was shifted downstream by `fst5cut + 1` bases (2 for EcoRI, 3 for NotI, etc.).

This matters whenever a researcher opens the exported GenBank file in SnapGene, ApE, or Benchling to verify a restriction digest strategy or select cloning sites: the displayed feature markers would not align with the actual enzyme recognition sequences.

**Fix:**
1. Built `_ENZYME_CUT_OFFSET` dict at import time: `{str(e): e.charac[0] for e in _CommOnly}` capturing `fst5cut` for each enzyme.
2. In the restriction site annotation loop, converted cut positions to 0-based recognition sequence starts:
   ```python
   recog_start = pos - fst5cut - 1
   ```
3. Added bounds check to skip wrap-around positions from circular sequence analysis that fall outside the sequence length (these arise when BioPython reports sites that span the circular join).

**Formula derivation:** For an enzyme cutting at position `k` within a recognition sequence of length `L` starting at 0-based index `s`:
- 1-based cut position returned by BioPython = `s + 1 + k` = `s + 1 + fst5cut`
- So: `s = pos - fst5cut - 1`

This holds for enzymes with negative `fst5cut` (cut upstream of recognition sequence, e.g., SapI) and for enzymes with `fst5cut=0` (blunt cutters, e.g., SmaI).

**Tests added:** `tests/unit/test_export.py` — `test_restriction_site_annotated_at_recognition_sequence_not_cut_site`:
- Constructs a sequence with EcoRI (GAATTC) at known 0-based position 5
- Obtains BioPython cut position via `Analysis.full()` (returns 7)
- Writes GenBank and reads it back
- Asserts `seq[feature_start : feature_start+6] == "GAATTC"`

**Result:** 424 passing, 0 warnings.

---

---

## Session 13 Fixes (2026-03-23) — Yeast selection media nomenclature

### Issue X — `_build_next_steps` writes "SC - URA3" (wrong) instead of "SC-URA" (correct)

**File:** `src/tools/gene_introduction.py:_build_next_steps`
**Biological rationale:** Yeast synthetic complete (SC) dropout media are named after the **nutrient omitted**, not the marker gene:
- Correct: SC-URA (lacks uracil), SC-LEU (lacks leucine), SC-HIS (lacks histidine), SC-TRP (lacks tryptophan)
- Wrong: SC-URA3, SC-LEU2, SC-HIS3, SC-TRP1

Using the gene name in dropout notation (e.g. "SC-URA3") is non-standard and would confuse any researcher ordering dropout powder from a supplier (Takara/Clontech, MP Biomedicals, US Biological all use nutrient names, not gene names). A new researcher following the protocol would not be able to find "SC-URA3" in a catalogue.

Additionally, dominant antibiotic resistance markers (kanMX, hygMX) do not use SC dropout media at all — they select on rich YPD medium plus antibiotic (G418 or Hygromycin B). The old step 4 text "SC - kanMX or antibiotic plates" is biologically nonsensical: there is no SC-kanMX dropout medium.

**Fix:**
Added `_YEAST_SELECTION_MEDIA` dict mapping each marker to the correct media description, then used it in step 4:
```python
_YEAST_SELECTION_MEDIA = {
    "URA3":  "SC-URA (synthetic complete medium lacking uracil)",
    "LEU2":  "SC-LEU (lacking leucine)",
    "HIS3":  "SC-HIS (lacking histidine)",
    "TRP1":  "SC-TRP (lacking tryptophan)",
    "kanMX": "YPD + G418 (200–400 mg/L)",
    "hygMX": "YPD + Hygromycin B (300 mg/L)",
}
```

Step 4 now reads: `f"4. Select transformants on {selection_media}."` — correct for all six markers.

**Tests added:** `tests/unit/test_gene_introduction.py` — `TestYeastSelectionMedia` (6 tests):
- URA3 → "SC-URA" present, "SC-URA3" absent
- LEU2 → "SC-LEU" present, "SC-LEU2" absent
- HIS3 → "SC-HIS" present, "SC-HIS3" absent
- TRP1 → "SC-TRP" present, "SC-TRP1" absent
- kanMX → "G418" present, "SC-kanMX" absent
- hygMX → "Hygromycin" present, "SC-hygMX" absent

**Result:** 430 passing, 0 warnings.

---

## Biosafety / Regulatory Notes

No red flags in current scope. The hosts covered (E. coli K-12, S. cerevisiae, A. thaliana/plant binary) are BSL-1 organisms under standard conditions. The CRISPR guide RNA tool generates sequences for SpCas9 targeting — no dual-use concern at this level of abstraction. Recommend maintaining this scope until mammalian or BSL-2 hosts are added, at which point a biosafety review layer should be added to the agent system prompt.
