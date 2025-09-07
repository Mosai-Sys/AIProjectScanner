param(
    [Parameter(Mandatory=$true)]
    [string]$RootPath,
    [Parameter(Mandatory=$true)]
    [string]$OutFile,
    [int]$MaxFileSizeMB = 3,
    [string[]]$BinaryExt = @(
        ".exe",".dll",".bin",".dat",".so",".dylib",
        ".png",".jpg",".jpeg",".gif",".bmp",".ico",".webp",
        ".pdf",".zip",".7z",".rar",".tar",".gz",".xz",
        ".mp3",".wav",".flac",".ogg",".mp4",".mkv",".mov",".avi",
        ".gguf",".onnx",".pt",".pth",".safetensors"
    )
)

function Get-Depth([string]$root, [string]$fullPath) {
    $rel = [System.IO.Path]::GetRelativePath($root, $fullPath)
    if ($rel -eq [System.IO.Path]::GetFileName($fullPath)) { return 0 }
    $sep = [System.IO.Path]::DirectorySeparatorChar
    return ($rel.Split($sep, [System.StringSplitOptions]::RemoveEmptyEntries).Count) - 1
}

function Test-IsBinaryByProbe([string]$path, [int]$probe=1024) {
    try {
        $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'Read')
        try {
            $len = [Math]::Min($probe, $fs.Length)
            $buf = New-Object byte[] $len
            [void]$fs.Read($buf, 0, $len)
            foreach ($b in $buf) { if ($b -eq 0) { return $true } }
            return $false
        } finally { $fs.Dispose() }
    } catch { return $true }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$RootPath  = (Resolve-Path $RootPath).Path
$maxBytes  = $MaxFileSizeMB * 1MB

$result = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    root         = $RootPath
    notes        = @(
        "Depth: rotmappe=0, første undernivå=1, osv.",
        "Rekkefølge: mapper alfabetisk, deretter filer alfabetisk per mappe.",
        "Filer > ${MaxFileSizeMB} MB: ingen innhold/preview – kun metadata (sti, endelse, dybde, størrelse).",
        "Tomme mapper og tomme filer inkluderes.",
        "Schema: se 'schema'."
    )
    schema       = @{
        item_object = @{
            type           = "directory | file"
            depth          = "0 = rot, 1 = undernivå, ..."
            path           = "Relativ sti fra root"
            is_empty       = "Kun for mapper"
            size_bytes     = "Kun for filer"
            ext            = "Filendelse"
            is_binary      = "Heuristikk + endelse"
            skipped_reason = "Angis når innhold ikke tas med (f.eks. 'too_large' eller 'binary')"
            content        = "Kun små tekstfiler (<= terskel). Aldri for store filer."
        }
    }
    items        = @()
}

# Rotmappe
$result.items += [ordered]@{ type="directory"; depth=0; path="."; is_empty=$false }

# Alle mapper (inkludert rot), sortert
$dirs = @($RootPath) + (Get-ChildItem -LiteralPath $RootPath -Recurse -Directory | Sort-Object FullName | ForEach-Object { $_.FullName })

foreach ($dir in $dirs) {
    if ($dir -ne $RootPath) {
        $relDir = [System.IO.Path]::GetRelativePath($RootPath, $dir)
        $result.items += [ordered]@{
            type="directory"; depth=(Get-Depth $RootPath $dir); path=$relDir; is_empty=$false
        }
    }

    $files = Get-ChildItem -LiteralPath $dir -File | Sort-Object Name
    if (-not $files -and $dir -ne $RootPath) {
        # Marker siste katalog som tom
        for ($i = $result.items.Count-1; $i -ge 0; $i--) {
            if ($result.items[$i].type -eq "directory" -and $result.items[$i].path -eq [System.IO.Path]::GetRelativePath($RootPath, $dir)) {
                $result.items[$i].is_empty = $true
                break
            }
        }
        continue
    }

    foreach ($f in $files) {
        $rel   = [System.IO.Path]::GetRelativePath($RootPath, $f.FullName)
        $ext   = ($f.Extension ?? "").ToLowerInvariant()
        $depth = Get-Depth $RootPath $f.FullName
        $size  = [int64]$f.Length

        $item = [ordered]@{
            type       = "file"
            depth      = $depth
            path       = $rel
            size_bytes = $size
            ext        = $ext
            is_binary  = $false
        }

        $isBin = ($BinaryExt -contains $ext) -or (Test-IsBinaryByProbe $f.FullName 1024)
        if ($isBin) {
            $item.is_binary = $true
            $item.skipped_reason = "binary"
            $result.items += $item
            continue
        }

        if ($size -gt $maxBytes) {
            # For store filer tar vi ikke med innhold/preview
            $item.skipped_reason = "too_large"
            $result.items += $item
            continue
        }

        # Liten tekstfil – les hele innholdet
        try {
            $text = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
        } catch {
            try {
                $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
                $text  = [System.Text.Encoding]::UTF8.GetString($bytes)
            } catch {
                $text = $null
            }
        }

        if ($null -eq $text) {
            $item.skipped_reason = "read_error"
        } else {
            $item.content = $text
        }

        $result.items += $item
    }
}

$json = $result | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($OutFile, $json, $utf8NoBom)
Write-Host "Ferdig. Output: $OutFile"
