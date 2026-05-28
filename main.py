"""
Crake — deterministic plasmid design workbench.

Standalone CLI entrypoints for each bioinformatics tool (also invoked by the
Streamlit app via slash commands):

    # Fetch starting sequence
    python src/tools/fetch_sequence.py --gene GFP --organism "Aequorea victoria"
    python src/tools/fetch_sequence.py --accession U55762
    python src/tools/fetch_sequence.py --accession NM_001301717 --full-sequence

    # Find edit site in target locus
    python src/tools/target_site.py --sequence ATCG... --method crispr
    python src/tools/target_site.py --sequence ATCG... --method restriction
    python src/tools/target_site.py --sequence ATCG... --method homologous --position 500

    # Design
    python src/tools/sequence_design.py --host e_coli --suggest-parts
    python src/tools/sequence_design.py --optimize-codons --sequence ATCG... --host plant_nuclear
    python src/tools/annotation.py --sequence ATCG... --restriction-sites
    python src/tools/primer_design.py --template ATCG... --overhang-f GCGC
    python src/tools/assembly.py --method gibson --parts insert.fa backbone.fa
    python src/tools/validation.py --sequence ATCG...

    # Export lab-ready artifacts
    python src/tools/export.py \
        --assembly assembly.json \
        --validation validation.json \
        --primers primers.json \
        --name pMyConstruct \
        --output-dir ./output/
    # Produces: pMyConstruct.gb, pMyConstruct.fa, pMyConstruct_map.svg, primers.csv, protocol.md

Run tests: uv run pytest
"""
