#!/bin/sh
# PoUW-SIREN — checagem de integridade dos artefatos publicados (Fases 1, 2 e 3).
# Recalcula o SHA-256 de todos os artefatos da pesquisa e compara com os
# valores registrados em hashes.sha256 (Fase 1, 15 âncoras),
# fase2/hashes_fase2.sha256 (Fase 2, 23 âncoras) e
# fase3/hashes_fase3.sha256 (Fase 3, 37 âncoras), no formato sha256sum -c.
#
# Uso (Linux/macOS):   bash checar_integridade.sh          → 75× OK
# Equivalente Linux:   sha256sum -c hashes.sha256 && sha256sum -c fase2/hashes_fase2.sha256 && sha256sum -c fase3/hashes_fase3.sha256
# Equivalente macOS:   shasum -a 256 -c hashes.sha256 && shasum -a 256 -c fase2/hashes_fase2.sha256 && shasum -a 256 -c fase3/hashes_fase3.sha256
# Windows:             certutil -hashfile receita_b0f90ffe.pt SHA256
#                      (comparar manualmente com os arquivos de hashes)

cd "$(dirname "$0")" || exit 1

if command -v sha256sum >/dev/null 2>&1; then
    CMD="sha256sum -c"
elif command -v shasum >/dev/null 2>&1; then
    CMD="shasum -a 256 -c"
else
    echo "ERRO: nem 'sha256sum' nem 'shasum' foram encontrados neste sistema."
    echo "Use 'certutil -hashfile <arquivo> SHA256' (Windows) e compare com os arquivos de hashes."
    exit 1
fi

echo "== Fase 1 (hashes.sha256) =="
$CMD hashes.sha256 || exit 1
echo
echo "== Fase 2 (fase2/hashes_fase2.sha256) =="
$CMD fase2/hashes_fase2.sha256 || exit 1
echo
echo "== Fase 3 (fase3/hashes_fase3.sha256) =="
$CMD fase3/hashes_fase3.sha256 || exit 1
