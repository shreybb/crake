"""Typed construct workflow session — single source of session truth."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class AssemblyProvenance(str, Enum):
    SIMULATED = "simulated"
    NOT_RUN = "not_run"


class WorkflowStage(str, Enum):
    EMPTY = "empty"
    LOADED = "loaded"
    OPTIMIZED = "optimized"
    VALIDATED = "validated"
    ASSEMBLED = "assembled"
    EXPORTED = "exported"


@dataclass
class LoadedSequence:
    sequence: str
    gene_name: str | None = None
    accession: str | None = None
    organism: str | None = None
    topology: Literal["circular", "linear"] = "linear"
    source: str = "unknown"
    length_bp: int | None = None
    suggested_host: str | None = None
    features: list[dict] = field(default_factory=list)
    sequence_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoadedSequence | None:
        if not data or data.get("error"):
            return None
        seq = data.get("sequence", "")
        if not seq:
            return None
        topo = data.get("topology", "linear")
        if topo not in ("circular", "linear"):
            topo = "linear"
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            sequence=seq,
            gene_name=data.get("gene_name"),
            accession=data.get("accession"),
            organism=data.get("organism"),
            topology=topo,
            source=data.get("source", "unknown"),
            length_bp=data.get("length_bp") or len(seq),
            suggested_host=data.get("suggested_host"),
            features=list(data.get("features") or []),
            sequence_type=data.get("sequence_type"),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "sequence": self.sequence,
            "length_bp": self.length_bp or len(self.sequence),
            "topology": self.topology,
            "source": self.source,
        }
        if self.gene_name:
            out["gene_name"] = self.gene_name
        if self.accession:
            out["accession"] = self.accession
        if self.organism:
            out["organism"] = self.organism
        if self.suggested_host:
            out["suggested_host"] = self.suggested_host
        if self.features:
            out["features"] = self.features
        if self.sequence_type:
            out["sequence_type"] = self.sequence_type
        out.update(self.extra)
        return out


@dataclass
class AssemblyRecord:
    product_sequence: str
    method: str
    success: bool
    provenance: AssemblyProvenance
    topology: str = "circular"
    fragments: list[str] = field(default_factory=list)
    product_length_bp: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssemblyRecord | None:
        if not data:
            return None
        raw_prov = data.get("provenance")
        if isinstance(raw_prov, AssemblyProvenance):
            provenance = raw_prov
        elif raw_prov == AssemblyProvenance.SIMULATED.value:
            provenance = AssemblyProvenance.SIMULATED
        elif raw_prov == AssemblyProvenance.NOT_RUN.value:
            provenance = AssemblyProvenance.NOT_RUN
        elif data.get("method") in ("gibson", "restriction_ligation") and data.get("success"):
            provenance = AssemblyProvenance.SIMULATED
        elif data.get("method") in ("sequence_only", "direct"):
            provenance = AssemblyProvenance.NOT_RUN
        else:
            provenance = AssemblyProvenance.NOT_RUN
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        extra = {k: v for k, v in data.items() if k not in known and k != "provenance"}
        return cls(
            product_sequence=data.get("product_sequence", ""),
            method=data.get("method", "unknown"),
            success=bool(data.get("success")),
            provenance=provenance,
            topology=data.get("topology", "circular"),
            fragments=list(data.get("fragments") or []),
            product_length_bp=data.get("product_length_bp"),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "product_sequence": self.product_sequence,
            "method": self.method,
            "success": self.success,
            "provenance": self.provenance.value,
            "topology": self.topology,
        }
        if self.fragments:
            out["fragments"] = self.fragments
        if self.product_length_bp is not None:
            out["product_length_bp"] = self.product_length_bp
        out.update(self.extra)
        return out


@dataclass
class ExportReadiness:
    can_export: bool
    stage: WorkflowStage
    warnings: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)


@dataclass
class ConstructSession:
    """Workflow state for one construct design session."""

    sequence: LoadedSequence | None = None
    optimization: dict[str, Any] | None = None
    assembly: AssemblyRecord | None = None
    validation: dict[str, Any] | None = None
    primers: dict[str, Any] | None = None
    annotation: dict[str, Any] | None = None
    gene_introduction: dict[str, Any] | None = None
    seqviz: dict[str, Any] | None = None
    export_paths: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_state_dict(cls, state: dict[str, Any]) -> ConstructSession:
        seq = LoadedSequence.from_dict(state.get("last_sequence") or {})
        asm = AssemblyRecord.from_dict(state.get("last_assembly") or {})
        return cls(
            sequence=seq,
            optimization=state.get("last_optimization"),
            assembly=asm,
            validation=state.get("last_validation"),
            primers=state.get("last_primers"),
            annotation=state.get("last_annotation"),
            gene_introduction=state.get("last_gene_introduction"),
            seqviz=state.get("last_seqviz"),
            export_paths=dict(state.get("export_paths") or {}),
        )

    def to_state_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "last_sequence": self.sequence.to_dict() if self.sequence else None,
            "last_optimization": self.optimization,
            "last_assembly": self.assembly.to_dict() if self.assembly else None,
            "last_validation": self.validation,
            "last_primers": self.primers,
            "last_annotation": self.annotation,
            "last_gene_introduction": self.gene_introduction,
            "last_seqviz": self.seqviz,
            "export_paths": self.export_paths,
        }
        return out

    def require_sequence(self) -> LoadedSequence:
        if not self.sequence or not self.sequence.sequence:
            raise ValueError(
                "No sequence loaded. Use `/genesearch`, `/fetch`, `/load`, "
                "or **Introduce a Gene** first."
            )
        return self.sequence

    def set_sequence_from_result(self, result: dict[str, Any], source: str) -> None:
        if result.get("error"):
            return
        loaded = LoadedSequence.from_dict({**result, "source": source})
        if loaded:
            self.sequence = loaded

    def promote_optimized(self, result: dict[str, Any]) -> None:
        self.optimization = result
        if result.get("error") or not result.get("optimized_sequence"):
            return
        prior = self.sequence
        meta = prior.to_dict() if prior else {}
        meta.pop("sequence", None)
        meta.pop("length_bp", None)
        self.sequence = LoadedSequence(
            sequence=result["optimized_sequence"],
            gene_name=meta.get("gene_name") or "optimized",
            accession=meta.get("accession"),
            organism=meta.get("organism"),
            topology=meta.get("topology", "linear"),
            source="optimize",
            length_bp=len(result["optimized_sequence"]),
            suggested_host=meta.get("suggested_host"),
            features=meta.get("features") or [],
            sequence_type=meta.get("sequence_type"),
            extra={k: v for k, v in meta.items() if k not in LoadedSequence.__dataclass_fields__},  # type: ignore[attr-defined]
        )

    def record_assembly(self, result: dict[str, Any]) -> None:
        if not result.get("success"):
            return
        rec = AssemblyRecord.from_dict({**result, "provenance": AssemblyProvenance.SIMULATED.value})
        if rec:
            self.assembly = rec

    def assembly_for_export(self, allow_sequence_only: bool = False) -> AssemblyRecord:
        """Build assembly payload for export_files."""
        if self.assembly and self.assembly.success and self.assembly.provenance == AssemblyProvenance.SIMULATED:
            return self.assembly
        seq = self.require_sequence()
        if not allow_sequence_only:
            raise ValueError(
                "Assembly has not been simulated. Run `/assemble gibson …` first, "
                "or use `/export <name> --allow-sequence-only` to export the loaded sequence only."
            )
        return AssemblyRecord(
            product_sequence=seq.sequence,
            method="sequence_only",
            success=True,
            provenance=AssemblyProvenance.NOT_RUN,
            topology=seq.topology,
        )

    def workflow_stage(self) -> WorkflowStage:
        if self.export_paths:
            return WorkflowStage.EXPORTED
        if self.assembly and self.assembly.success and self.assembly.provenance == AssemblyProvenance.SIMULATED:
            return WorkflowStage.ASSEMBLED
        if self.validation:
            return WorkflowStage.VALIDATED
        if self.optimization and not self.optimization.get("error"):
            return WorkflowStage.OPTIMIZED
        if self.sequence:
            return WorkflowStage.LOADED
        return WorkflowStage.EMPTY

    def export_readiness(self) -> ExportReadiness:
        warnings: list[str] = []
        blocks: list[str] = []
        try:
            self.require_sequence()
        except ValueError as exc:
            return ExportReadiness(
                can_export=False,
                stage=WorkflowStage.EMPTY,
                blocks=[str(exc)],
            )
        if not self.validation:
            warnings.append("Validation not run — export will auto-validate.")
        if not self.primers or not self.primers.get("primer_pairs"):
            warnings.append("No primers designed — primer CSV may be omitted.")
        asm_simulated = (
            self.assembly
            and self.assembly.success
            and self.assembly.provenance == AssemblyProvenance.SIMULATED
        )
        if not asm_simulated:
            warnings.append(
                "Assembly not simulated — export is sequence-only; verify in silico before ordering."
            )
        return ExportReadiness(
            can_export=True,
            stage=self.workflow_stage(),
            warnings=warnings,
            blocks=blocks,
        )
