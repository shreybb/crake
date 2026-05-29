# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| 0.1.x   | Best effort |

## Reporting a vulnerability

If you find a security issue in Crake, please **do not** open a public GitHub issue.

Email **103163688+shreybb@users.noreply.github.com** with:

- Description of the issue and impact
- Steps to reproduce
- Affected version or commit

We will acknowledge within a few business days and work on a fix or mitigation.

## Scope notes

Crake runs locally as a Streamlit app. It fetches public sequences from NCBI Entrez and UniProt when you use fetch/genesearch commands. Do not commit `.env` files or API keys.

This tool assists with **research plasmid design**. It is not a substitute for institutional biosafety review. Users are responsible for compliance with local regulations for their organisms and sequences.
