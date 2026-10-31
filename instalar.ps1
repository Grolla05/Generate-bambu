#Requires -Version 5.1
<#
.SYNOPSIS
    Instala a skill generate-bambu nos agentes detectados e liga o MCP do Fusion.

.DESCRIPTION
    Usa um canal só por agente: com plugin ou extensão presente, não copia a skill
    nem grava o MCP (a cópia de usuário esconderia as atualizações do plugin).
    Mostra o plano e pede confirmação antes de gravar. Faz backup de todo arquivo
    de configuração que altera. Nunca exibe valores desses arquivos: eles têm tokens.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\instalar.ps1 -Simular

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\instalar.ps1 -Agentes codex,antigravity

.PARAMETER Agentes
    Lista separada por vírgula: claude, codex, gemini, antigravity, agy. Padrão: todos.

.PARAMETER Simular
    Só mostra o plano, sem gravar nada.

.PARAMETER Sim
    Aplica sem pedir confirmação.

.PARAMETER Desinstalar
    Remove só o que este script instalou (marcador na pasta, bloco no arquivo).

.PARAMETER McpClaude
    Registra o MCP do Fusion no Claude Code com `claude mcp add`. Fica fora do padrão
    porque duplicaria a extensão do Fusion em quem usa o app desktop.

.PARAMETER RaizHome
    Pasta do usuário. Serve para testar sem tocar na sua configuração real.
#>
[CmdletBinding()]
param(
    [string[]] $Agentes,
    [switch] $Simular,
    [switch] $Sim,
    [switch] $Desinstalar,
    [switch] $McpClaude,
    [string] $RaizHome = $env:USERPROFILE,
    [Parameter(DontShow)] [AllowEmptyString()] [string] $BinariosTeste
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$NOME = 'generate-bambu'
$URL_FUSION = 'http://127.0.0.1:27182/mcp'
$MARCADOR = '.instalado-por-generate-bambu'
$INICIO_TOML = '# >>> generate-bambu'
$FIM_TOML = '# <<< generate-bambu'
$AGENTES_VALIDOS = 'claude', 'codex', 'gemini', 'antigravity', 'agy'

if (-not $PSScriptRoot) {
    throw 'Rode a partir de um clone do repositório: o script precisa da pasta skills/.'
}
$ORIGEM = Join-Path $PSScriptRoot "skills\$NOME"
if (-not (Test-Path -LiteralPath (Join-Path $ORIGEM 'SKILL.md'))) {
    throw "Skill não encontrada em $ORIGEM."
}

$script:binariosFixos = $null
if ($PSBoundParameters.ContainsKey('BinariosTeste')) {
    $script:binariosFixos = @($BinariosTeste -split ',' | Where-Object { $_ })
}

# -File entrega "a,b" como um argumento só.
$escolhidos = $AGENTES_VALIDOS
if ($Agentes) {
    $escolhidos = @($Agentes -join ',' -split ',' | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ })
    foreach ($a in $escolhidos) {
        if ($AGENTES_VALIDOS -notcontains $a) {
            throw "Agente desconhecido: $a. Use: $($AGENTES_VALIDOS -join ', ')."
        }
    }
}

function Caminho([string] $relativo) { Join-Path $RaizHome $relativo }

function Existe([string] $caminho) { Test-Path -LiteralPath $caminho }

function Tem-Binario([string] $nome) {
    if ($null -ne $script:binariosFixos) { return $script:binariosFixos -contains $nome }
    return [bool](Get-Command $nome -ErrorAction SilentlyContinue)
}

function E-Link([string] $caminho) {
    $atributos = (Get-Item -LiteralPath $caminho -Force).Attributes
    return [bool]($atributos -band [IO.FileAttributes]::ReparsePoint)
}

function Ler-Texto([string] $caminho) {
    return [IO.File]::ReadAllText($caminho, [Text.Encoding]::UTF8)
}

function Escrever-Texto([string] $caminho, [string] $texto) {
    [void][IO.Directory]::CreateDirectory((Split-Path -Parent $caminho))
    $temporario = "$caminho.tmp-$PID"
    # Set-Content -Encoding UTF8 põe BOM no 5.1, e Gemini e Codex não aceitam.
    [IO.File]::WriteAllText($temporario, $texto, (New-Object Text.UTF8Encoding $false))
    if (Existe $caminho) {
        $backup = "$caminho.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
        [IO.File]::Replace($temporario, $caminho, $backup)
        return
    }
    [IO.File]::Move($temporario, $caminho)
}

function Propriedade($objeto, [string] $nome) {
    if ($null -eq $objeto -or $objeto -isnot [Management.Automation.PSCustomObject]) { return $null }
    $encontrada = $objeto.PSObject.Properties[$nome]
    if ($encontrada) { return $encontrada.Value }
    return $null
}

function Ler-Json([string] $texto) {
    # A mensagem de erro do ConvertFrom-Json cita trechos do arquivo: não pode vazar.
    try { return ConvertFrom-Json -InputObject $texto } catch { return $null }
}

function Estado-Json([string] $caminho, [string[]] $chavesUrl) {
    if (-not (Existe $caminho)) { return 'inserir' }
    $dados = Ler-Json (Ler-Texto $caminho)
    if ($dados -isnot [Management.Automation.PSCustomObject]) { return 'invalido' }
    $servidores = $dados.PSObject.Properties['mcpServers']
    if (-not $servidores) { return 'inserir' }
    if ($servidores.Value -isnot [Management.Automation.PSCustomObject]) { return 'invalido' }
    $fusion = $servidores.Value.PSObject.Properties['fusion']
    if (-not $fusion) { return 'inserir' }
    foreach ($chave in $chavesUrl) {
        if ((Propriedade $fusion.Value $chave) -eq $URL_FUSION) { return 'igual' }
    }
    return 'divergente'
}

# Só chamada depois de validar o texto como JSON, então as aspas sempre fecham.
function Achar-Objeto([string] $texto, [string] $chave) {
    $profundidade = 0
    $i = 0
    while ($i -lt $texto.Length) {
        $c = $texto[$i]
        if ($c -eq '"') {
            $inicio = ++$i
            while ($texto[$i] -ne '"') {
                if ($texto[$i] -eq '\') { $i++ }
                $i++
            }
            $valor = $texto.Substring($inicio, $i - $inicio)
            $i++
            if ($profundidade -eq 1 -and $valor -ceq $chave) {
                $resto = $texto.Substring($i).TrimStart()
                if ($resto.StartsWith(':') -and $resto.Substring(1).TrimStart().StartsWith('{')) {
                    return $texto.IndexOf('{', $i) + 1
                }
            }
            continue
        }
        if ($c -eq '{' -or $c -eq '[') { $profundidade++ }
        elseif ($c -eq '}' -or $c -eq ']') { $profundidade-- }
        $i++
    }
    return -1
}

# Insere por texto em vez de ConvertTo-Json: o resto do arquivo não muda um byte.
function Inserir-Json([string] $texto, [string] $chaveUrl) {
    $quebra = "`n"
    if ($texto.Contains("`r`n")) { $quebra = "`r`n" }
    $bloco = '"fusion": { "' + $chaveUrl + '": "' + $URL_FUSION + '" }'

    $posicao = Achar-Objeto $texto 'mcpServers'
    if ($posicao -ge 0) {
        $separador = ','
        if ($texto.Substring($posicao).TrimStart().StartsWith('}')) { $separador = '' }
        return $texto.Insert($posicao, "$quebra    $bloco$separador")
    }

    $posicao = $texto.IndexOf('{') + 1
    $separador = ','
    if ($texto.Substring($posicao).TrimStart().StartsWith('}')) { $separador = '' }
    return $texto.Insert($posicao, "$quebra  `"mcpServers`": {$quebra    $bloco$quebra  }$separador")
}

function Gravar-Json([string] $caminho, [string] $chaveUrl) {
    $texto = "{`n}`n"
    if (Existe $caminho) { $texto = Ler-Texto $caminho }
    $novo = Inserir-Json $texto $chaveUrl
    if ($null -eq (Ler-Json $novo)) { throw "Resultado inválido; $caminho ficou intacto." }
    Escrever-Texto $caminho $novo
}

function Remover-Json([string] $caminho, [string[]] $chavesUrl) {
    $texto = Ler-Texto $caminho
    foreach ($chave in $chavesUrl) {
        $corpo = '"fusion"\s*:\s*\{\s*"' + $chave + '"\s*:\s*"' + [regex]::Escape($URL_FUSION) + '"\s*\}'
        foreach ($padrao in @("\s*$corpo\s*,", ",\s*$corpo", "\s*$corpo")) {
            $regex = New-Object regex $padrao
            if ($regex.IsMatch($texto)) {
                $novo = $regex.Replace($texto, '', 1)
                if ($null -eq (Ler-Json $novo)) { throw "Resultado inválido; $caminho ficou intacto." }
                Escrever-Texto $caminho $novo
                return
            }
        }
    }
    throw "Entrada fusion de $caminho foi alterada à mão; remova você mesmo."
}

function Estado-Toml([string] $caminho) {
    if (-not (Existe $caminho)) { return 'inserir' }
    $texto = Ler-Texto $caminho
    $url = 'url\s*=\s*["'']' + [regex]::Escape($URL_FUSION) + '["'']'
    $secao = [regex]::Match($texto, '(?ms)^[ \t]*\[mcp_servers\."?fusion"?\][ \t]*\r?\n(.*?)(?=^[ \t]*\[|\z)')
    if ($secao.Success) {
        if ($secao.Groups[1].Value -match $url) { return 'igual' }
        return 'divergente'
    }
    $pontilhada = $texto -match '(?m)^[ \t]*mcp_servers\.fusion[ \t]*[.=]'
    $inline = $texto -match '(?m)^[ \t]*mcp_servers[ \t]*=[ \t]*\{[^\r\n]*\bfusion\b'
    if ($pontilhada -or $inline) {
        if ($texto -match [regex]::Escape($URL_FUSION)) { return 'igual' }
        return 'divergente'
    }
    return 'inserir'
}

function Gravar-Toml([string] $caminho) {
    $texto = ''
    if (Existe $caminho) { $texto = Ler-Texto $caminho }
    $quebra = "`n"
    if ($texto.Contains("`r`n")) { $quebra = "`r`n" }
    if ($texto -and -not $texto.EndsWith("`n")) { $texto += $quebra }
    $linhas = '', $INICIO_TOML, '[mcp_servers.fusion]', "url = `"$URL_FUSION`"", $FIM_TOML, ''
    Escrever-Texto $caminho ($texto + ($linhas -join $quebra))
}

function Remover-Toml([string] $caminho) {
    $padrao = '(?s)\r?\n?' + [regex]::Escape($INICIO_TOML) + '.*?' + [regex]::Escape($FIM_TOML) + '\r?\n?'
    Escrever-Texto $caminho ([regex]::Replace((Ler-Texto $caminho), $padrao, ''))
}

function Copiar-Skill([string] $destino, [string] $versao) {
    [void][IO.Directory]::CreateDirectory((Split-Path -Parent $destino))
    # Copy-Item sobre pasta existente aninha em vez de substituir: monta ao lado e troca.
    $temporario = "$destino.tmp-$PID"
    if (Existe $temporario) { Remove-Item -LiteralPath $temporario -Recurse -Force }
    [void][IO.Directory]::CreateDirectory($temporario)
    Get-ChildItem -LiteralPath $ORIGEM -Recurse -Force |
        Where-Object { $_.FullName -notmatch '\\__pycache__(\\|$)' -and $_.Extension -ne '.pyc' } |
        ForEach-Object {
            $alvo = Join-Path $temporario $_.FullName.Substring($ORIGEM.Length).TrimStart('\')
            if ($_.PSIsContainer) { [void][IO.Directory]::CreateDirectory($alvo) }
            else { [IO.File]::Copy($_.FullName, $alvo, $true) }
        }
    [IO.File]::WriteAllText((Join-Path $temporario $MARCADOR), $versao)

    $antigo = "$destino.old-$PID"
    if (Existe $destino) { [IO.Directory]::Move($destino, $antigo) }
    [IO.Directory]::Move($temporario, $destino)
    if (Existe $antigo) { Remove-Item -LiteralPath $antigo -Recurse -Force }
}

function Rodar-Claude([string] $argumentos) {
    # cmd para não trazer a saída: `claude mcp` pode listar valores de configuração.
    & cmd /c "claude $argumentos >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

$plano = New-Object Collections.ArrayList

function Planejar([string] $agente, [string] $acao, [string] $alvo, [string] $detalhe) {
    [void]$plano.Add([pscustomobject]@{ Agente = $agente; Acao = $acao; Alvo = $alvo; Detalhe = $detalhe })
}

function Plugin-Presente([string] $agente) {
    switch ($agente) {
        'claude' {
            $registro = Caminho '.claude\plugins\installed_plugins.json'
            return (Existe $registro) -and ((Ler-Texto $registro) -match "`"$NOME@")
        }
        'codex' {
            $config = Caminho '.codex\config.toml'
            return (Existe $config) -and ((Ler-Texto $config) -match "(?m)^\[plugins\.`"$NOME@")
        }
        'gemini' { return Existe (Caminho ".gemini\extensions\$NOME") }
        default { return Existe (Caminho ".gemini\config\plugins\$NOME") }
    }
}

function Detectado([string] $agente) {
    switch ($agente) {
        'claude' { return (Tem-Binario 'claude') -or (Existe (Caminho '.claude')) }
        'codex' { return (Tem-Binario 'codex') -or (Existe (Caminho '.codex\config.toml')) }
        # ~/.gemini também nasce com o Antigravity, então a pasta não prova o Gemini CLI.
        'gemini' { return Tem-Binario 'gemini' }
        'antigravity' { return Existe (Caminho '.gemini\config') }
        'agy' { return (Tem-Binario 'agy') -or (Existe (Caminho '.gemini\antigravity-cli')) }
    }
}

function Pasta-Skill([string] $agente) {
    switch ($agente) {
        'claude' { return Caminho ".claude\skills\$NOME" }
        'codex' { return Caminho ".agents\skills\$NOME" }
        'gemini' { return Caminho ".gemini\skills\$NOME" }
        'antigravity' { return Caminho ".gemini\config\skills\$NOME" }
        'agy' { return Caminho ".gemini\antigravity-cli\skills\$NOME" }
    }
}

function Planejar-Copia([string] $agente) {
    $destino = Pasta-Skill $agente
    if (-not (Existe $destino)) { Planejar $agente 'copiar' $destino 'skill'; return }
    if (E-Link $destino) { Planejar $agente 'erro' $destino 'destino é um link; recusado'; return }
    if (-not (Existe (Join-Path $destino $MARCADOR))) {
        Planejar $agente 'aviso' $destino 'pasta não foi criada por este script; mantida'
        return
    }
    Planejar $agente 'copiar' $destino 'atualiza a skill'
}

function Planejar-Mcp([string] $agente, [string] $tipo, [string] $caminho, [string] $chave) {
    $estado = if ($tipo -eq 'toml') { Estado-Toml $caminho } else { Estado-Json $caminho @($chave) }
    switch ($estado) {
        'inserir' { Planejar $agente $tipo $caminho $chave }
        'igual' { Planejar $agente 'pular' $caminho 'MCP do Fusion já configurado' }
        'divergente' { Planejar $agente 'aviso' $caminho 'já existe fusion com outro valor; mantido' }
        'invalido' { Planejar $agente 'erro' $caminho 'não é JSON puro (comentários?); adicione o MCP à mão' }
    }
}

function Montar-Instalacao {
    $compartilhada = Existe (Pasta-Skill 'codex')
    if (($escolhidos -contains 'codex') -and (Detectado 'codex') -and -not (Plugin-Presente 'codex')) {
        $compartilhada = $true
    }
    $mcpAntigravity = $false

    foreach ($agente in $escolhidos) {
        if (-not (Detectado $agente)) { Planejar $agente 'pular' '' 'não detectado'; continue }
        if ($agente -eq 'claude' -and $McpClaude) {
            if (Tem-Binario 'claude') { Planejar 'claude' 'mcp-claude' 'claude mcp add' 'fusion' }
            else { Planejar 'claude' 'erro' '' '-McpClaude exige o binário claude no PATH' }
        }
        if (Plugin-Presente $agente) {
            Planejar $agente 'pular' '' 'plugin ou extensão já presente'
            if ($agente -eq 'codex') {
                $plugins = [regex]::Matches((Ler-Texto (Caminho '.codex\config.toml')), "(?m)^\[plugins\.`"$NOME@")
                if ($plugins.Count -gt 1) {
                    Planejar 'codex' 'aviso' '' "$($plugins.Count) plugins $NOME ativos; desative os que sobram no app"
                }
            }
            continue
        }

        # ~/.agents/skills também é lido por Gemini e Antigravity (não pelo agy).
        if ($compartilhada -and @('gemini', 'antigravity') -contains $agente) {
            Planejar $agente 'pular' '' 'skill já vem de ~/.agents/skills'
        }
        else {
            Planejar-Copia $agente
        }

        switch ($agente) {
            'codex' { Planejar-Mcp 'codex' 'toml' (Caminho '.codex\config.toml') 'url' }
            'gemini' { Planejar-Mcp 'gemini' 'json' (Caminho '.gemini\settings.json') 'httpUrl' }
            { 'antigravity', 'agy' -contains $_ } {
                # IDE e CLI leem o mesmo arquivo.
                if (-not $mcpAntigravity) {
                    Planejar-Mcp $agente 'json' (Caminho '.gemini\config\mcp_config.json') 'serverUrl'
                    $mcpAntigravity = $true
                }
            }
        }
    }
}

function Montar-Desinstalacao {
    foreach ($agente in $escolhidos) {
        $destino = Pasta-Skill $agente
        if (Existe $destino) {
            if (E-Link $destino) { Planejar $agente 'erro' $destino 'destino é um link; recusado' }
            elseif (Existe (Join-Path $destino $MARCADOR)) { Planejar $agente 'remover' $destino 'skill' }
            else { Planejar $agente 'aviso' $destino 'pasta não foi criada por este script; mantida' }
        }
    }
    if ($escolhidos -contains 'codex') {
        $config = Caminho '.codex\config.toml'
        if ((Existe $config) -and (Ler-Texto $config).Contains($INICIO_TOML)) {
            Planejar 'codex' 'remover-toml' $config 'MCP do Fusion'
        }
    }
    if ($escolhidos -contains 'gemini') {
        $config = Caminho '.gemini\settings.json'
        if ((Estado-Json $config @('httpUrl')) -eq 'igual') { Planejar 'gemini' 'remover-json' $config 'httpUrl' }
    }
    if (($escolhidos -contains 'antigravity') -or ($escolhidos -contains 'agy')) {
        $config = Caminho '.gemini\config\mcp_config.json'
        if ((Estado-Json $config @('serverUrl')) -eq 'igual') { Planejar 'antigravity' 'remover-json' $config 'serverUrl' }
    }
    if ($McpClaude) {
        if (Tem-Binario 'claude') { Planejar 'claude' 'mcp-claude-remover' 'claude mcp remove' 'fusion' }
        else { Planejar 'claude' 'erro' '' '-McpClaude exige o binário claude no PATH' }
    }
}

function Aplicar($item, [string] $versao) {
    switch ($item.Acao) {
        'copiar' { Copiar-Skill $item.Alvo $versao }
        'toml' { Gravar-Toml $item.Alvo }
        'json' { Gravar-Json $item.Alvo $item.Detalhe }
        'remover' { Remove-Item -LiteralPath $item.Alvo -Recurse -Force }
        'remover-toml' { Remover-Toml $item.Alvo }
        'remover-json' { Remover-Json $item.Alvo @($item.Detalhe) }
        'mcp-claude' {
            if (-not (Rodar-Claude 'mcp get fusion')) {
                if (-not (Rodar-Claude "mcp add --transport http --scope user fusion $URL_FUSION")) {
                    throw 'claude mcp add falhou.'
                }
            }
        }
        'mcp-claude-remover' {
            if (-not (Rodar-Claude 'mcp remove --scope user fusion')) { throw 'claude mcp remove falhou.' }
        }
    }
}

$versao = (ConvertFrom-Json -InputObject (Ler-Texto (Join-Path $PSScriptRoot '.claude-plugin\plugin.json'))).version
if ($Desinstalar) { Montar-Desinstalacao } else { Montar-Instalacao }

$modo = if ($Desinstalar) { 'desinstalar' } else { 'instalar' }
Write-Host "$NOME ${versao}: plano para $modo"
foreach ($item in $plano) {
    Write-Host ('  [{0}] {1}: {2} {3}' -f $item.Acao, $item.Agente, $item.Alvo, $item.Detalhe)
}

$pendentes = @($plano | Where-Object { @('pular', 'aviso', 'erro') -notcontains $_.Acao })
$erros = @($plano | Where-Object { $_.Acao -eq 'erro' }).Count

if ($Simular) {
    Write-Host 'Simulação: nada foi gravado.'
    exit ([int]($erros -gt 0))
}
if ($pendentes.Count -eq 0) {
    Write-Host 'Nada a fazer.'
    exit ([int]($erros -gt 0))
}
if (@($pendentes | Where-Object { $_.Acao -like '*toml' }).Count -gt 0) {
    Write-Host 'Feche o app do Codex antes: ele pode reescrever o config.toml aberto.'
}
if (-not $Sim) {
    $resposta = Read-Host 'Aplicar? [s/N]'
    if ($resposta -notmatch '^(s|sim|y|yes)$') {
        Write-Host 'Cancelado: nada foi gravado.'
        exit 0
    }
}

foreach ($item in $pendentes) {
    try {
        Aplicar $item $versao
        Write-Host ('  ok: {0} {1}' -f $item.Agente, $item.Alvo)
    }
    catch {
        $erros++
        Write-Host ('  falhou: {0} {1}: {2}' -f $item.Agente, $item.Alvo, $_.Exception.Message)
    }
}

if ($erros -gt 0) {
    Write-Host "Terminou com $erros erro(s)."
    exit 1
}
Write-Host 'Pronto. Reinicie os agentes para carregar a skill.'
exit 0
