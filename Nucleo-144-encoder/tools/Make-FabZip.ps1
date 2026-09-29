<#
.SYNOPSIS
    Zips the fab outputs that the JLCPCB-PCBWay OutJob just wrote.

.DESCRIPTION
    Called by MakeFabZip.pas after the OutJob runs. Takes every file under -Source
    written at or after -Since, keeps the Gerber / NC Drill subfolders, and writes
    them to -Zip, replacing any older zip. Older files left in -Source by a previous
    run are skipped, so a stale layer cannot reach the fab.

    The window is hidden, so the result is reported in a message box.

.EXAMPLE
    .\Make-FabZip.ps1 -Source "..\Project Outputs for X\JLCPCB-PCBWay" -Zip "..\Project Outputs for X\X.zip" -Since 20260927150000
#>
param(
    [Parameter(Mandatory)] [string] $Source,
    [Parameter(Mandatory)] [string] $Zip,
    # yyyyMMddHHmmss, taken by the Altium script just before the OutJob ran
    [Parameter(Mandatory)] [string] $Since
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

try {
    # Slack for clock skew between Altium and the file system (e.g. a VM shared folder)
    $cutoff = [datetime]::ParseExact($Since, 'yyyyMMddHHmmss', $null).AddSeconds(-120)
    $Source = $Source.TrimEnd('\')
    $files  = @(Get-ChildItem -LiteralPath $Source -Recurse -File |
                Where-Object { $_.LastWriteTime -ge $cutoff })
    if ($files.Count -eq 0) {
        throw "Nothing under $Source was written after $cutoff. Did the OutJob run?"
    }

    $stage = Join-Path ([IO.Path]::GetTempPath()) ('fabzip-' + [guid]::NewGuid())
    foreach ($f in $files) {
        $dir = Join-Path $stage $f.DirectoryName.Substring($Source.Length).TrimStart('\')
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Copy-Item -LiteralPath $f.FullName -Destination $dir
    }

    if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
    Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $Zip
    Remove-Item -LiteralPath $stage -Recurse -Force

    [System.Windows.Forms.MessageBox]::Show("$($files.Count) files zipped to`n$Zip", 'Fab zip') | Out-Null
}
catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Fab zip failed') | Out-Null
    exit 1
}
