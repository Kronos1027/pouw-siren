#!/bin/sh
# PoUW-SIREN Fase 1 — checagem de integridade dos artefatos publicados.
# Recalcula o SHA-256 de todos os artefatos da pesquisa e compara com os valores
# registrados no relatorio_fase1.md (seção 6), no formato sha256sum -c.
#
# Uso (Linux/macOS):   bash checar_integridade.sh
# Equivalente Linux:   sha256sum -c hashes.sha256
# Equivalente macOS:   shasum -a 256 -c hashes.sha256
# Windows:             certutil -hashfile receita_b0f90ffe.pt SHA256
#                      (comparar manualmente com hashes.sha256)

cd "$(dirname "$0")" || exit 1

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c hashes.sha256
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c hashes.sha256
else
    echo "ERRO: nem 'sha256sum' nem 'shasum' foram encontrados neste sistema."
    echo "Use 'certutil -hashfile <arquivo> SHA256' (Windows) e compare com hashes.sha256."
    exit 1
fi
