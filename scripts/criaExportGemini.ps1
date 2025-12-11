# ==============================================================================
# Script: gerar_log.ps1
# Objetivo: Ler todos os arquivos .py da pasta, escrever o nome e o conteúdo
#           em um único arquivo de saída para facilitar o envio ao Gemini.
# ==============================================================================

# 1. Definições
$extensao = "*.py"                  # Tipo de arquivo a ser lido
$arquivoSaida = "CONTEXTO_PROJETO.txt" # Nome do arquivo de log final

# 2. Limpeza inicial (remove o log anterior se existir)
if (Test-Path $arquivoSaida) {
    Remove-Item $arquivoSaida
    Write-Host "Arquivo de log anterior removido." -ForegroundColor Yellow
}

# 3. Obter lista de arquivos
$arquivos = Get-ChildItem -Path . -Filter $extensao

# 4. Loop para processar cada arquivo
foreach ($arq in $arquivos) {
    # Ignora o próprio script se por acaso ele for salvo como .py (segurança)
    if ($arq.Name -eq "gerar_log.py") { continue }

    # Formatando o Cabeçalho do arquivo
    $header = @"

==============================================================================
NOME DO ARQUIVO: $($arq.Name)
==============================================================================

"@
    
    # Escreve o cabeçalho no arquivo de saída (UTF-8)
    Add-Content -Path $arquivoSaida -Value $header -Encoding UTF8

    # Lê o conteúdo do arquivo original
    $conteudo = Get-Content -Path $arq.FullName -Raw -Encoding UTF8

    # Escreve o conteúdo no arquivo de saída
    Add-Content -Path $arquivoSaida -Value $conteudo -Encoding UTF8
}

# 5. Finalização
Write-Host "Processo concluído!" -ForegroundColor Green
Write-Host "O conteúdo de todos os arquivos '$extensao' foi salvo em: $arquivoSaida" -ForegroundColor Cyan