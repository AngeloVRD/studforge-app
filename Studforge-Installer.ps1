#Requires -Version 5.0
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ── Konfiguration ────────────────────────────────────────────────────────────
$GITHUB_ZIP  = 'https://github.com/AngeloVRD/studforge-app/archive/refs/heads/main.zip'
$PYTHON_URL  = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
$INSTALL_DIR = Join-Path $env:LOCALAPPDATA 'Programs\Studforge'
$TEMP_DIR    = Join-Path $env:TEMP "StudforgeSetup_$PID"

# ── Farben ───────────────────────────────────────────────────────────────────
$C_BG     = [Drawing.Color]::FromArgb(10, 10, 10)
$C_BG2    = [Drawing.Color]::FromArgb(20, 20, 20)
$C_BG3    = [Drawing.Color]::FromArgb(35, 35, 35)
$C_ORANGE = [Drawing.Color]::FromArgb(249, 115, 22)
$C_WHITE  = [Drawing.Color]::White
$C_GRAY   = [Drawing.Color]::FromArgb(140, 140, 140)
$C_GREEN  = [Drawing.Color]::FromArgb(34, 197, 94)
$C_RED    = [Drawing.Color]::FromArgb(239, 68, 68)
$C_DIM    = [Drawing.Color]::FromArgb(80, 80, 80)

# ── Python suchen ────────────────────────────────────────────────────────────
function Find-Python {
    $paths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python39\python.exe'),
        'C:\Python311\python.exe', 'C:\Python312\python.exe',
        'C:\Python310\python.exe', 'C:\Python39\python.exe'
    )
    foreach ($p in $paths) { if (Test-Path $p) { return $p } }
    try {
        $p = (Get-Command python -ErrorAction Stop).Source
        if ($p -notlike '*WindowsApps*') { return $p }
    } catch {}
    return $null
}

# ── Form ─────────────────────────────────────────────────────────────────────
$form = New-Object Windows.Forms.Form
$form.Text            = 'Studforge Setup'
$form.ClientSize      = New-Object Drawing.Size(560, 500)
$form.BackColor       = $C_BG
$form.ForeColor       = $C_WHITE
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox     = $false
$form.StartPosition   = 'CenterScreen'
$form.Font            = New-Object Drawing.Font('Segoe UI', 10)

# Icon aus dem selben Ordner laden (falls vorhanden)
$selfDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$icoPath = Join-Path $selfDir 'icon.ico'
if (Test-Path $icoPath) {
    try { $form.Icon = New-Object Drawing.Icon($icoPath) } catch {}
}

# ── Header ───────────────────────────────────────────────────────────────────
$pnlHeader = New-Object Windows.Forms.Panel
$pnlHeader.Dock      = 'Top'
$pnlHeader.Height    = 104
$pnlHeader.BackColor = $C_BG2
$form.Controls.Add($pnlHeader)

$pnlAccent = New-Object Windows.Forms.Panel  # orange Linie unten
$pnlAccent.Dock      = 'Bottom'
$pnlAccent.Height    = 2
$pnlAccent.BackColor = $C_ORANGE
$pnlHeader.Controls.Add($pnlAccent)

$lblTitle = New-Object Windows.Forms.Label
$lblTitle.Text      = 'Studforge'
$lblTitle.Font      = New-Object Drawing.Font('Segoe UI', 24, [Drawing.FontStyle]::Bold)
$lblTitle.ForeColor = $C_ORANGE
$lblTitle.Location  = New-Object Drawing.Point(24, 12)
$lblTitle.AutoSize  = $true
$pnlHeader.Controls.Add($lblTitle)

$lblSub = New-Object Windows.Forms.Label
$lblSub.Text      = '3D Druck Management  ·  Installations-Assistent'
$lblSub.Font      = New-Object Drawing.Font('Segoe UI', 9)
$lblSub.ForeColor = $C_GRAY
$lblSub.Location  = New-Object Drawing.Point(27, 62)
$lblSub.AutoSize  = $true
$pnlHeader.Controls.Add($lblSub)

# ── Zielordner ───────────────────────────────────────────────────────────────
$pnlDir = New-Object Windows.Forms.Panel
$pnlDir.Location  = New-Object Drawing.Point(20, 116)
$pnlDir.Size      = New-Object Drawing.Size(520, 22)
$form.Controls.Add($pnlDir)

$lblDirKey = New-Object Windows.Forms.Label
$lblDirKey.Text      = 'Installiert in:'
$lblDirKey.ForeColor = $C_DIM
$lblDirKey.Location  = New-Object Drawing.Point(0, 3)
$lblDirKey.AutoSize  = $true
$pnlDir.Controls.Add($lblDirKey)

$lblDirVal = New-Object Windows.Forms.Label
$lblDirVal.Text      = $INSTALL_DIR
$lblDirVal.ForeColor = $C_WHITE
$lblDirVal.Location  = New-Object Drawing.Point(96, 3)
$lblDirVal.AutoSize  = $true
$pnlDir.Controls.Add($lblDirVal)

# ── Log-Box ──────────────────────────────────────────────────────────────────
$rtbLog = New-Object Windows.Forms.RichTextBox
$rtbLog.Location    = New-Object Drawing.Point(20, 148)
$rtbLog.Size        = New-Object Drawing.Size(520, 230)
$rtbLog.BackColor   = $C_BG2
$rtbLog.ForeColor   = $C_GRAY
$rtbLog.ReadOnly    = $true
$rtbLog.Font        = New-Object Drawing.Font('Consolas', 9)
$rtbLog.BorderStyle = 'None'
$rtbLog.ScrollBars  = 'Vertical'
$form.Controls.Add($rtbLog)

# ── Fortschrittsbalken (orange, custom) ──────────────────────────────────────
$pnlPBg = New-Object Windows.Forms.Panel
$pnlPBg.Location  = New-Object Drawing.Point(20, 392)
$pnlPBg.Size      = New-Object Drawing.Size(520, 14)
$pnlPBg.BackColor = $C_BG3
$form.Controls.Add($pnlPBg)

$pnlPFill = New-Object Windows.Forms.Panel
$pnlPFill.Location  = New-Object Drawing.Point(0, 0)
$pnlPFill.Size      = New-Object Drawing.Size(0, 14)
$pnlPFill.BackColor = $C_ORANGE
$pnlPBg.Controls.Add($pnlPFill)

$lblPct = New-Object Windows.Forms.Label
$lblPct.Text      = '0 %'
$lblPct.ForeColor = $C_DIM
$lblPct.Font      = New-Object Drawing.Font('Segoe UI', 8)
$lblPct.Location  = New-Object Drawing.Point(20, 410)
$lblPct.AutoSize  = $true
$form.Controls.Add($lblPct)

# ── Buttons ──────────────────────────────────────────────────────────────────
$btnInstall = New-Object Windows.Forms.Button
$btnInstall.Text      = '  Installieren'
$btnInstall.Size      = New-Object Drawing.Size(160, 40)
$btnInstall.Location  = New-Object Drawing.Point(252, 446)
$btnInstall.BackColor = $C_ORANGE
$btnInstall.ForeColor = [Drawing.Color]::FromArgb(15,15,15)
$btnInstall.FlatStyle = 'Flat'
$btnInstall.FlatAppearance.BorderSize  = 0
$btnInstall.FlatAppearance.MouseOverBackColor = [Drawing.Color]::FromArgb(234, 100, 8)
$btnInstall.Font      = New-Object Drawing.Font('Segoe UI', 10, [Drawing.FontStyle]::Bold)
$form.Controls.Add($btnInstall)

$btnCancel = New-Object Windows.Forms.Button
$btnCancel.Text      = 'Abbrechen'
$btnCancel.Size      = New-Object Drawing.Size(110, 40)
$btnCancel.Location  = New-Object Drawing.Point(430, 446)
$btnCancel.BackColor = $C_BG3
$btnCancel.ForeColor = $C_GRAY
$btnCancel.FlatStyle = 'Flat'
$btnCancel.FlatAppearance.BorderSize = 0
$form.Controls.Add($btnCancel)

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────
function Write-Log($text, $col = $null) {
    if ($null -eq $col) { $col = $C_GRAY }
    $rtbLog.SelectionStart  = $rtbLog.TextLength
    $rtbLog.SelectionLength = 0
    $rtbLog.SelectionColor  = $col
    $rtbLog.AppendText("$text`n")
    $rtbLog.ScrollToCaret()
    [Windows.Forms.Application]::DoEvents()
}

function Set-Progress($pct) {
    $pct = [Math]::Max(0, [Math]::Min(100, $pct))
    $pnlPFill.Width = [int]($pnlPBg.Width * $pct / 100)
    $lblPct.Text    = "$pct %"
    [Windows.Forms.Application]::DoEvents()
}

$global:installDone = $false

# ── Installations-Logik ──────────────────────────────────────────────────────
function Start-Install {
    $btnInstall.Enabled = $false
    $btnCancel.Enabled  = $false
    $global:installDone = $false

    try {
        # 1 — Python ─────────────────────────────────────────────────
        Write-Log '● Python wird gesucht ...' $C_WHITE
        Set-Progress 5
        $python = Find-Python

        if ($python) {
            Write-Log "  ✓ Gefunden: $python" $C_GREEN
        } else {
            Write-Log '  Nicht gefunden. Python 3.11 wird heruntergeladen ...' $C_GRAY
            Set-Progress 8
            $pyInst = Join-Path $env:TEMP 'python-3.11.9-amd64.exe'
            Invoke-WebRequest -Uri $PYTHON_URL -OutFile $pyInst -UseBasicParsing
            Write-Log '  Installer wird ausgeführt (bitte warten) ...' $C_GRAY
            $proc = Start-Process $pyInst `
                -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1' `
                -Wait -PassThru
            Remove-Item $pyInst -ErrorAction SilentlyContinue
            if ($proc.ExitCode -ne 0) {
                throw "Python-Installation fehlgeschlagen (Exit-Code $($proc.ExitCode))"
            }
            $python = Find-Python
            if (-not $python) { throw 'Python konnte nach Installation nicht gefunden werden.' }
            Write-Log "  ✓ Python installiert: $python" $C_GREEN
        }
        Set-Progress 22

        # 2 — Download von GitHub ─────────────────────────────────────
        Write-Log '● App wird von GitHub geladen ...' $C_WHITE
        if (Test-Path $TEMP_DIR) { Remove-Item $TEMP_DIR -Recurse -Force }
        New-Item $TEMP_DIR -ItemType Directory | Out-Null
        $zipPath = Join-Path $TEMP_DIR 'studforge.zip'
        Invoke-WebRequest -Uri $GITHUB_ZIP -OutFile $zipPath -UseBasicParsing
        Write-Log '  ✓ Download abgeschlossen' $C_GREEN
        Set-Progress 45

        # 3 — Entpacken ───────────────────────────────────────────────
        Write-Log '● Dateien werden entpackt ...' $C_WHITE
        Expand-Archive -Path $zipPath -DestinationPath $TEMP_DIR -Force
        $extracted = Get-ChildItem $TEMP_DIR -Directory | Select-Object -First 1
        if (-not $extracted) { throw 'Entpackter Ordner nicht gefunden.' }

        if (Test-Path $INSTALL_DIR) { Remove-Item $INSTALL_DIR -Recurse -Force }
        Copy-Item $extracted.FullName $INSTALL_DIR -Recurse
        Write-Log "  ✓ Installiert in: $INSTALL_DIR" $C_GREEN
        Set-Progress 62

        # 4 — Pakete ──────────────────────────────────────────────────
        Write-Log '● Flask & PyWebView werden installiert ...' $C_WHITE
        & $python -m pip install flask pywebview --quiet 2>&1 | Out-Null
        Write-Log '  ✓ Pakete installiert' $C_GREEN
        Set-Progress 78

        # 5 — Icon ────────────────────────────────────────────────────
        Write-Log '● App-Icon wird generiert ...' $C_WHITE
        & $python (Join-Path $INSTALL_DIR 'icon.py') 2>&1 | Out-Null
        Write-Log '  ✓ Icon erstellt' $C_GREEN
        Set-Progress 90

        # 6 — Shortcut ────────────────────────────────────────────────
        Write-Log '● Desktop-Verknüpfung wird erstellt ...' $C_WHITE
        $pythonw = $python -replace 'python\.exe$', 'pythonw.exe'
        if (-not (Test-Path $pythonw)) { $pythonw = $python }
        $ws  = New-Object -ComObject WScript.Shell
        $dsk = [Environment]::GetFolderPath('Desktop')
        $sc  = $ws.CreateShortcut("$dsk\Studforge.lnk")
        $sc.TargetPath       = $pythonw
        $sc.Arguments        = "`"$(Join-Path $INSTALL_DIR 'main.py')`""
        $sc.WorkingDirectory = $INSTALL_DIR
        $sc.IconLocation     = Join-Path $INSTALL_DIR 'icon.ico'
        $sc.Description      = 'Studforge 3D Manufaktur'
        $sc.Save()
        Write-Log "  ✓ Verknüpfung auf dem Desktop erstellt" $C_GREEN
        Set-Progress 100

        # Fertig ──────────────────────────────────────────────────────
        Write-Log ''
        Write-Log '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' $C_ORANGE
        Write-Log '  Studforge wurde erfolgreich installiert!' $C_GREEN
        Write-Log '  Klicke "Starten" oder nutze die Desktop-Verknüpfung.' $C_GRAY
        Write-Log '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' $C_ORANGE

        $global:installDone   = $true
        $btnInstall.Text      = '  Starten  ▶'
        $btnInstall.Enabled   = $true
        $btnCancel.Text       = 'Schliessen'
        $btnCancel.Enabled    = $true

    } catch {
        Write-Log ''
        Write-Log "  ✗ Fehler: $_" $C_RED
        $btnInstall.Text    = '  Wiederholen'
        $btnInstall.Enabled = $true
        $btnCancel.Enabled  = $true
    } finally {
        Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# ── Events ───────────────────────────────────────────────────────────────────
$btnInstall.Add_Click({
    if ($global:installDone) {
        $python = Find-Python
        if ($python) {
            $pythonw = $python -replace 'python\.exe$', 'pythonw.exe'
            if (-not (Test-Path $pythonw)) { $pythonw = $python }
            Start-Process $pythonw `
                -ArgumentList "`"$(Join-Path $INSTALL_DIR 'main.py')`"" `
                -WorkingDirectory $INSTALL_DIR
        }
        $form.Close()
    } else {
        $rtbLog.Clear()
        Start-Install
    }
})

$btnCancel.Add_Click({ $form.Close() })

# ── Startmeldung ─────────────────────────────────────────────────────────────
Write-Log 'Willkommen beim Studforge Installations-Assistenten.' $C_WHITE
Write-Log ''
Write-Log 'Was wird installiert:' $C_GRAY
Write-Log '  · Python 3.11  (falls nicht vorhanden)' $C_DIM
Write-Log '  · Flask + PyWebView' $C_DIM
Write-Log '  · Studforge App-Dateien' $C_DIM
Write-Log '  · Desktop-Verknüpfung mit Icon' $C_DIM
Write-Log ''
Write-Log 'Klicke "Installieren" um zu starten.' $C_GRAY

[Windows.Forms.Application]::EnableVisualStyles()
[Windows.Forms.Application]::Run($form)
