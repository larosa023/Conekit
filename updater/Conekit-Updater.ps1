<#
  Conekit installer + updater for VLC 3 on Windows.

  First run : asks Dark or Light, installs to %APPDATA%\vlc\skins, switches VLC to the skin,
              and offers to check for updates automatically every day.
  Later runs: checks GitHub for a newer version and updates in place.

  Switches:
    -Silent       No prompts or windows (used by the daily check). Only updates the skin files.
    -Variant X    Dark or Light (skip the question).
    -Force        Re-download even if already up to date.
    -Uninstall    Remove the skins, the daily check, and switch VLC back to its normal look.
#>
param(
    [switch]$Silent,
    [ValidateSet("Dark", "Light")][string]$Variant,
    [switch]$Force,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Repo      = "larosa023/Conekit"
$RawBase   = "https://raw.githubusercontent.com/$Repo/main"
$VlcDir    = Join-Path $env:APPDATA "vlc"
$SkinDir   = Join-Path $VlcDir "skins"
$StateFile = Join-Path $SkinDir "conekit.json"
$VlcRc     = Join-Path $VlcDir "vlcrc"
$TaskName  = "Conekit skin updater"
$SelfDest  = Join-Path $SkinDir "Conekit-Updater.ps1"
$HiddenVbs = Join-Path $SkinDir "Conekit-Updater-silent.vbs"
$Programs  = [Environment]::GetFolderPath("Programs")
if (-not $Programs) { $Programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs" }
$Shortcut  = Join-Path $Programs "Conekit Updater.lnk"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Say($msg, $color = "Gray") { if (-not $Silent) { Write-Host $msg -ForegroundColor $color } }

function Ask($question, $default) {
    if ($Silent) { return $default }
    $a = Read-Host $question
    if ([string]::IsNullOrWhiteSpace($a)) { return $default }
    return $a.Trim()
}

function Get-State {
    if (Test-Path $StateFile) {
        try { return Get-Content $StateFile -Raw | ConvertFrom-Json } catch { }
    }
    return $null
}

function Save-State($version, $variant, $auto) {
    $obj = [ordered]@{ version = $version; variant = $variant; autoUpdate = [bool]$auto }
    [IO.File]::WriteAllText($StateFile, ($obj | ConvertTo-Json), $Utf8NoBom)
}

function Get-Remote($path) {
    $url = "$RawBase/$path" + "?nocache=" + [guid]::NewGuid().ToString("N")
    return Invoke-WebRequest -Uri $url -UseBasicParsing -Headers @{ "Cache-Control" = "no-cache" }
}

function Compare-Version($a, $b) {
    try { return ([version]$a).CompareTo([version]$b) } catch { return [string]::Compare($a, $b) }
}

function Write-Lines($path, $lines) { [IO.File]::WriteAllLines($path, [string[]]$lines, $Utf8NoBom) }

function Set-Option([string[]]$lines, $section, $key, $value) {
    # Replace "key=" or "#key=" inside [section]; otherwise add it right under the section header.
    $out = New-Object System.Collections.Generic.List[string]
    $cur = ""; $done = $false
    foreach ($l in $lines) {
        if ($l -match '^\[(.+)\]') { $cur = $Matches[1] }
        if (-not $done -and $cur -eq $section -and $l -match "^#?$([regex]::Escape($key))=") {
            $out.Add("$key=$value"); $done = $true
        } else { $out.Add($l) }
    }
    if (-not $done) {
        $idx = $out.IndexOf("[$section]")
        if ($idx -ge 0) { $out.Insert($idx + 1, "$key=$value") }
        else { $out.Add(""); $out.Add("[$section]"); $out.Add("$key=$value") }
    }
    return ,$out.ToArray()
}

function Set-VlcConfig($skinPath) {
    # VLC rewrites vlcrc when it exits, so only edit it while VLC is closed.
    if (-not (Test-Path $VlcRc)) {
        Say "  VLC's settings file isn't there yet. Open and close VLC once, then run this again." "Yellow"
        return $false
    }
    Copy-Item $VlcRc "$VlcRc.conekit-backup" -Force
    $lines = [IO.File]::ReadAllLines($VlcRc)
    $lines = Set-Option $lines "core" "intf" "skins"
    $lines = Set-Option $lines "skins2" "skins2-last" $skinPath
    Write-Lines $VlcRc $lines
    return $true
}

function Reset-VlcConfig {
    if (-not (Test-Path $VlcRc)) { return }
    $lines = [IO.File]::ReadAllLines($VlcRc) | ForEach-Object {
        if ($_ -eq "intf=skins") { "#intf=" }
        elseif ($_ -match '^skins2-last=.*Conekit') { "#skins2-last=" }
        else { $_ }
    }
    Write-Lines $VlcRc $lines
}

function Wait-VlcClosed {
    $p = Get-Process -Name vlc -ErrorAction SilentlyContinue
    if (-not $p) { return $true }
    if ($Silent) { return $false }
    Say ""
    Say "VLC is open. Close VLC so the switch can be saved." "Yellow"
    $a = Ask "Press Enter after closing VLC (or type S to skip switching the look)" ""
    if ($a -match '^[sS]') { return $false }
    while (Get-Process -Name vlc -ErrorAction SilentlyContinue) {
        Say "Still open... waiting." "DarkGray"; Start-Sleep -Seconds 2
    }
    return $true
}

function Register-DailyCheck {
    # A tiny VBScript launcher runs PowerShell with no window, so the daily check never flashes a console.
    $ps = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
    $vbs = 'CreateObject("WScript.Shell").Run """' + $ps + '"" -NoProfile -ExecutionPolicy Bypass -File ""' + $SelfDest + '"" -Silent", 0, False'
    [IO.File]::WriteAllText($HiddenVbs, $vbs, [Text.Encoding]::ASCII)
    $action  = New-ScheduledTaskAction -Execute (Join-Path $env:WINDIR "System32\wscript.exe") -Argument "`"$HiddenVbs`""
    $trigger = New-ScheduledTaskTrigger -Daily -At 12:17pm
    $set     = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $set `
        -Description "Checks GitHub for new Conekit VLC skin versions." -Force | Out-Null
}

function Unregister-DailyCheck {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    Remove-Item $HiddenVbs -ErrorAction SilentlyContinue
}

function New-StartShortcut {
    try {
        $ps = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
        $sh = (New-Object -ComObject WScript.Shell).CreateShortcut($Shortcut)
        $sh.TargetPath = $ps
        $sh.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$SelfDest`""
        $sh.Description = "Update Conekit or switch between Dark and Light"
        $vlcExe = Join-Path $env:ProgramFiles "VideoLAN\VLC\vlc.exe"
        if (Test-Path $vlcExe) { $sh.IconLocation = "$vlcExe,0" }
        $sh.Save()
    } catch { }
}

# ------------------------------------------------------------------ main
try {
    if ($Uninstall) {
        Say "Removing Conekit..." "Cyan"
        Unregister-DailyCheck
        Remove-Item $Shortcut -ErrorAction SilentlyContinue
        if (Wait-VlcClosed) { Reset-VlcConfig }
        Get-ChildItem $SkinDir -Filter "Conekit*" -ErrorAction SilentlyContinue | Remove-Item -Force
        Remove-Item $StateFile -ErrorAction SilentlyContinue
        Say "Done. VLC will use its normal look next time it starts." "Green"
        if (-not $Silent) { Read-Host "Press Enter to close" | Out-Null }
        exit 0
    }

    New-Item -ItemType Directory -Force -Path $SkinDir | Out-Null
    $state = Get-State
    $firstRun = ($null -eq $state)

    Say ""
    Say "  Conekit for VLC" "Cyan"
    Say "  -----------------" "DarkGray"

    $remote = (Get-Remote "VERSION").Content.Trim()
    $local  = if ($state) { $state.version } else { "none" }
    Say "  Installed: $local    Latest: $remote"

    if (-not $Variant) {
        $saved = if ($state -and $state.variant) { $state.variant } else { "Dark" }
        $v = Ask "  Which look? [D]ark or [L]ight (Enter = $saved)" $saved
        $Variant = if ($v -match '^[lL]') { "Light" } elseif ($v -match '^[dD]') { "Dark" } else { $saved }
    }

    $needsUpdate = $Force -or $firstRun -or ((Compare-Version $remote $local) -gt 0) `
        -or -not (Test-Path (Join-Path $SkinDir "Conekit-$Variant.vlt"))

    if ($needsUpdate) {
        Say "  Downloading Conekit $remote..." "Cyan"
        foreach ($name in @("Conekit-Dark.vlt", "Conekit-Light.vlt")) {
            $tmp = Join-Path $env:TEMP ("$name." + [guid]::NewGuid().ToString("N"))
            $url = "$RawBase/dist/$name" + "?nocache=" + [guid]::NewGuid().ToString("N")
            Invoke-WebRequest -Uri $url -UseBasicParsing -OutFile $tmp
            if ((Get-Item $tmp).Length -lt 10000) { throw "Download of $name looks incomplete." }
            Move-Item $tmp (Join-Path $SkinDir $name) -Force
        }
        # keep the updater itself current, so the daily check uses the newest logic
        try {
            $tmp = Join-Path $env:TEMP ("updater." + [guid]::NewGuid().ToString("N") + ".ps1")
            Invoke-WebRequest -Uri "$RawBase/updater/Conekit-Updater.ps1" -UseBasicParsing -OutFile $tmp
            Move-Item $tmp $SelfDest -Force
        } catch { }
        Say "  Updated to $remote." "Green"
    } else {
        Say "  Already up to date." "Green"
        if ($PSCommandPath -and ($PSCommandPath -ne $SelfDest)) { Copy-Item $PSCommandPath $SelfDest -Force }
    }

    $auto = if ($state) { [bool]$state.autoUpdate } else { $false }
    if ($firstRun -and -not $Silent) {
        $a = Ask "  Check for Conekit updates automatically (once a day, in the background)? [Y/n]" "Y"
        $auto = -not ($a -match '^[nN]')
        if ($auto) {
            try { Register-DailyCheck; Say "  Automatic updates are on." "Green" }
            catch { $auto = $false; Say "  Couldn't turn on automatic updates ($($_.Exception.Message)). Run this updater by hand instead." "Yellow" }
        }
    }

    Save-State $remote $Variant $auto
    if (-not (Test-Path $SelfDest) -and $PSCommandPath) { Copy-Item $PSCommandPath $SelfDest -Force }
    if (-not $Silent) { New-StartShortcut }

    if (-not $Silent) {
        $skinPath = Join-Path $SkinDir "Conekit-$Variant.vlt"
        $current = ""
        if (Test-Path $VlcRc) {
            $m = Select-String -Path $VlcRc -Pattern '^skins2-last=(.*)$' | Select-Object -First 1
            if ($m) { $current = $m.Matches[0].Groups[1].Value }
        }
        if ($current -ne $skinPath -or $firstRun) {
            if (Wait-VlcClosed) {
                if (Set-VlcConfig $skinPath) { Say "  VLC is set to use Conekit $Variant." "Green" }
            } else {
                Say "  Skipped switching. You can pick the skin in VLC: Tools > Preferences > Interface > Use custom skin:" "Yellow"
                Say "    $skinPath" "Yellow"
            }
        }
        Say ""
        Say "  All set. Start VLC to see it." "Cyan"
        Say "  Run this updater again any time (Start > Conekit Updater) to update or switch Dark/Light." "DarkGray"
        Read-Host "  Press Enter to close" | Out-Null
    }
    exit 0
}
catch {
    if ($Silent) { exit 1 }
    Write-Host ""
    Write-Host "  Something went wrong: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Check your internet connection and try again." -ForegroundColor Red
    Read-Host "  Press Enter to close" | Out-Null
    exit 1
}
