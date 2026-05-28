"""Unit tests for fetch_sequence tool."""
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from src.tools.fetch_sequence import (
    fetch_by_accession,
    fetch_from_uniprot,
    infer_host,
    search_gene,
    _extract_cds,
)


# ---------------------------------------------------------------------------
# Helpers: minimal BioPython-like fakes
# ---------------------------------------------------------------------------

def _make_gb_record(seq: str, organism: str, name: str = "ABC123", cds_seq: str = "") -> MagicMock:
    """Return a mock SeqRecord with optional CDS feature."""
    record = MagicMock()
    record.id = name
    record.name = name
    record.description = f"Mock {name}"
    record.annotations = {"organism": organism}
    record.seq = MagicMock()
    record.seq.__str__ = lambda self: seq

    if cds_seq:
        feat = MagicMock()
        feat.type = "CDS"
        feat.extract.return_value = MagicMock(__str__=lambda self: cds_seq)
        record.features = [feat]
    else:
        record.features = []

    return record


GFP_CDS = (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGAC"
    "GGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTAC"
)

NPTII_CDS = "ATGATTGAACAAGATGGATTGCACGCAGG"  # short mock


# ---------------------------------------------------------------------------
# infer_host
# ---------------------------------------------------------------------------

class TestInferHost:
    def test_agrobacterium_organism(self):
        assert infer_host("Agrobacterium tumefaciens") == "agrobacterium"

    def test_arabidopsis(self):
        assert infer_host("Arabidopsis thaliana") == "agrobacterium"

    def test_tobacco(self):
        assert infer_host("Nicotiana tabacum") == "agrobacterium"

    def test_ecoli_default(self):
        assert infer_host("Escherichia coli") == "e_coli"

    def test_unknown_defaults_to_ecoli(self):
        assert infer_host("Unknown species") == "e_coli"

    def test_case_insensitive(self):
        assert infer_host("ARABIDOPSIS THALIANA") == "agrobacterium"

    # Yeast host inference (Issue G fix)
    def test_saccharomyces_cerevisiae(self):
        """S. cerevisiae genes should suggest yeast host, not e_coli."""
        assert infer_host("Saccharomyces cerevisiae") == "yeast"

    def test_schizosaccharomyces_pombe(self):
        assert infer_host("Schizosaccharomyces pombe") == "yeast"

    def test_pichia_pastoris(self):
        assert infer_host("Pichia pastoris") == "yeast"

    def test_kluyveromyces(self):
        assert infer_host("Kluyveromyces lactis") == "yeast"

    def test_yeast_keyword_case_insensitive(self):
        assert infer_host("SACCHAROMYCES CEREVISIAE") == "yeast"

    def test_plant_takes_priority_over_yeast_keyword(self):
        """Plant keywords should still map to agrobacterium."""
        assert infer_host("Arabidopsis thaliana") == "agrobacterium"


# ---------------------------------------------------------------------------
# _extract_cds
# ---------------------------------------------------------------------------

class TestExtractCds:
    def test_extracts_cds_when_present(self):
        record = _make_gb_record("GGGGGG", "E. coli", cds_seq=GFP_CDS)
        seq, seq_type = _extract_cds(record)
        assert seq == GFP_CDS.upper()
        assert seq_type == "CDS"

    def test_falls_back_to_genomic(self):
        record = _make_gb_record("ATCGATCG", "E. coli")
        seq, seq_type = _extract_cds(record)
        assert seq_type == "genomic"


# ---------------------------------------------------------------------------
# fetch_by_accession — mocked NCBI
# ---------------------------------------------------------------------------

class TestFetchByAccession:
    def _mock_read(self, record):
        """Context manager that returns record from SeqIO.read."""
        return patch("src.tools.fetch_sequence.SeqIO.read", return_value=record)

    def _mock_efetch(self):
        return patch(
            "src.tools.fetch_sequence.Entrez.efetch",
            return_value=StringIO("FAKE_GENBANK"),
        )

    def test_returns_sequence_and_host(self):
        record = _make_gb_record("GENOMIC", "Agrobacterium tumefaciens", "U55762", GFP_CDS)
        with self._mock_efetch(), self._mock_read(record):
            result = fetch_by_accession("U55762")
        assert result["sequence"] == GFP_CDS.upper()
        assert result["suggested_host"] == "agrobacterium"
        assert result["sequence_type"] == "CDS"

    def test_full_sequence_flag_returns_genomic(self):
        record = _make_gb_record("ATCGATCGATCG", "Arabidopsis thaliana", "AT1G01020", GFP_CDS)
        with self._mock_efetch(), self._mock_read(record):
            result = fetch_by_accession("AT1G01020", full_sequence=True)
        # full_sequence=True bypasses CDS extraction
        assert result["sequence_type"] == "genomic"

    def test_ecoli_organism_maps_to_ecoli_host(self):
        record = _make_gb_record("ATCG", "Escherichia coli", "NP_000001")
        with self._mock_efetch(), self._mock_read(record):
            result = fetch_by_accession("NP_000001", db="protein")
        assert result["suggested_host"] == "e_coli"

    def test_returns_error_on_exception(self):
        with patch(
            "src.tools.fetch_sequence.Entrez.efetch", side_effect=Exception("timeout")
        ):
            result = fetch_by_accession("BAD_ACC")
        assert "error" in result
        assert result["accession"] == "BAD_ACC"

    def test_result_has_required_keys(self):
        record = _make_gb_record("ATCG", "Escherichia coli", "X00001", NPTII_CDS)
        with self._mock_efetch(), self._mock_read(record):
            result = fetch_by_accession("X00001")
        for key in ("accession", "gene_name", "organism", "sequence", "suggested_host"):
            assert key in result


# ---------------------------------------------------------------------------
# search_gene — mocked NCBI
# ---------------------------------------------------------------------------

class TestSearchGene:
    def _mock_esearch(self, ids=("12345",)):
        return patch(
            "src.tools.fetch_sequence.Entrez.esearch",
            return_value=StringIO("FAKE"),
        )

    def _mock_entrez_read(self, ids=("12345",)):
        return patch(
            "src.tools.fetch_sequence.Entrez.read",
            return_value={"IdList": list(ids)},
        )

    def _mock_fetch_accession(self, result: dict):
        return patch(
            "src.tools.fetch_sequence.fetch_by_accession",
            return_value=result,
        )

    def test_successful_search_returns_sequence(self):
        expected = {
            "accession": "U55762",
            "sequence": GFP_CDS,
            "suggested_host": "agrobacterium",
        }
        with (
            self._mock_esearch(),
            self._mock_entrez_read(["12345"]),
            self._mock_fetch_accession(expected),
            patch("src.tools.fetch_sequence.time.sleep"),
        ):
            result = search_gene("GFP", "Aequorea victoria")
        assert result["sequence"] == GFP_CDS
        assert "search_query" in result

    def test_no_results_returns_error(self):
        with (
            self._mock_esearch(),
            self._mock_entrez_read([]),
            patch("src.tools.fetch_sequence.time.sleep"),
        ):
            result = search_gene("NONEXISTENT", "Unknown species")
        assert "error" in result

    def test_search_query_metadata_added(self):
        expected = {"accession": "X1", "sequence": "ATCG", "suggested_host": "e_coli"}
        with (
            self._mock_esearch(),
            self._mock_entrez_read(["X1"]),
            self._mock_fetch_accession(expected),
            patch("src.tools.fetch_sequence.time.sleep"),
        ):
            result = search_gene("nptII", "Agrobacterium tumefaciens")
        assert result.get("search_query") == {
            "gene": "nptII",
            "organism": "Agrobacterium tumefaciens",
        }


# ---------------------------------------------------------------------------
# fetch_from_uniprot — mocked HTTP
# ---------------------------------------------------------------------------

UNIPROT_FASTA = (
    ">sp|P42212|GFP_AEQVI Green fluorescent protein OS=Aequorea victoria OX=6100\n"
    "MVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPT\n"
    "LVTTLTYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLV\n"
)


class TestFetchFromUniprot:
    def _mock_urlopen(self, fasta: str = UNIPROT_FASTA):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = fasta.encode("utf-8")
        return patch("src.tools.fetch_sequence.urllib.request.urlopen", return_value=mock_resp)

    def test_returns_protein_sequence(self):
        with self._mock_urlopen():
            result = fetch_from_uniprot("P42212")
        assert result["sequence_type"] == "protein"
        assert result["accession"] == "P42212"
        assert len(result["sequence"]) > 0

    def test_extracts_organism_from_header(self):
        with self._mock_urlopen():
            result = fetch_from_uniprot("P42212")
        assert "Aequorea victoria" in result["organism"]

    def test_includes_downstream_note(self):
        with self._mock_urlopen():
            result = fetch_from_uniprot("P42212")
        assert "note" in result
        assert "optimize-codons" in result["note"]

    def test_suggested_host_for_plant_protein(self):
        # GFP from Aequorea victoria — not a plant keyword, should default to e_coli
        with self._mock_urlopen():
            result = fetch_from_uniprot("P42212")
        # Aequorea victoria is not in plant keywords
        assert result["suggested_host"] == "e_coli"

    def test_returns_error_on_network_failure(self):
        with patch(
            "src.tools.fetch_sequence.urllib.request.urlopen",
            side_effect=Exception("connection refused"),
        ):
            result = fetch_from_uniprot("P00001")
        assert "error" in result

    def test_db_field_is_uniprot(self):
        with self._mock_urlopen():
            result = fetch_from_uniprot("P42212")
        assert result["db"] == "uniprot"
