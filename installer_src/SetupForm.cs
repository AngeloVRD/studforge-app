using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;
using System.Runtime.InteropServices;

static class Program
{
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();

    [STAThread]
    static void Main()
    {
        try { SetProcessDPIAware(); } catch { }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new SetupForm());
    }
}

class SetupForm : Form
{
    // ── Config ────────────────────────────────────────────────────────────────
    const string GITHUB_ZIP = "https://github.com/AngeloVRD/studforge-app/archive/refs/heads/main.zip";
    const string PYTHON_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe";

    static readonly string INSTALL_DIR = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        @"Programs\Studforge");

    static readonly string TEMP_DIR = Path.Combine(
        Path.GetTempPath(), "StudforgeSetup_" + System.Diagnostics.Process.GetCurrentProcess().Id);

    // ── Colours ───────────────────────────────────────────────────────────────
    static readonly Color BG     = Color.FromArgb(10,  10,  10);
    static readonly Color BG2    = Color.FromArgb(20,  20,  20);
    static readonly Color BG3    = Color.FromArgb(35,  35,  35);
    static readonly Color ORANGE = Color.FromArgb(249, 115,  22);
    static readonly Color WHITE  = Color.White;
    static readonly Color GRAY   = Color.FromArgb(140, 140, 140);
    static readonly Color DIM    = Color.FromArgb(70,   70,  70);
    static readonly Color GREEN  = Color.FromArgb(34,  197,  94);
    static readonly Color RED    = Color.FromArgb(239,  68,  68);

    // ── Controls ──────────────────────────────────────────────────────────────
    Panel       pnlProgressBg, pnlProgressFill;
    Label       lblPct, lblStatus;
    RichTextBox rtbLog;
    Button      btnAction, btnCancel;
    bool        installDone = false;

    // ─────────────────────────────────────────────────────────────────────────
    public SetupForm()
    {
        BuildUI();
        ShowWelcome();
    }

    // ── UI layout ─────────────────────────────────────────────────────────────
    void BuildUI()
    {
        Text            = "Studforge Setup";
        ClientSize      = new Size(560, 520);
        BackColor       = BG;
        ForeColor       = WHITE;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox     = false;
        StartPosition   = FormStartPosition.CenterScreen;
        Font            = new Font("Segoe UI", 10f);

        // Load window icon from same folder as exe
        try {
            string ico = Path.Combine(
                Path.GetDirectoryName(Application.ExecutablePath), "icon.ico");
            if (File.Exists(ico)) Icon = new Icon(ico);
        } catch { }

        // ── Header ────────────────────────────────────────────────────────────
        var header = new Panel { Dock = DockStyle.Top, Height = 108, BackColor = BG2 };
        var accent = new Panel { Dock = DockStyle.Bottom, Height = 2, BackColor = ORANGE };
        header.Controls.Add(accent);

        header.Controls.Add(new Label {
            Text = "Studforge", AutoSize = true, Location = new Point(24, 14),
            Font = new Font("Segoe UI", 26f, FontStyle.Bold), ForeColor = ORANGE
        });
        header.Controls.Add(new Label {
            Text = "3D Druck Management  ·  Installations-Assistent",
            AutoSize = true, Location = new Point(27, 68),
            Font = new Font("Segoe UI", 9f), ForeColor = GRAY
        });
        Controls.Add(header);

        // ── Install path label ────────────────────────────────────────────────
        Controls.Add(new Label {
            Text = "Installiert in:", ForeColor = DIM,
            Location = new Point(22, 122), AutoSize = true
        });
        Controls.Add(new Label {
            Text = INSTALL_DIR, ForeColor = GRAY,
            Location = new Point(116, 122), AutoSize = true,
            Font = new Font("Segoe UI", 9f)
        });

        // ── Status line ───────────────────────────────────────────────────────
        lblStatus = new Label {
            Text = "", ForeColor = GRAY,
            Location = new Point(22, 146), AutoSize = true,
            Font = new Font("Segoe UI", 9f)
        };
        Controls.Add(lblStatus);

        // ── Log box ───────────────────────────────────────────────────────────
        rtbLog = new RichTextBox {
            Location    = new Point(20, 168),
            Size        = new Size(520, 226),
            BackColor   = BG2,
            ForeColor   = GRAY,
            ReadOnly    = true,
            Font        = new Font("Consolas", 9f),
            BorderStyle = BorderStyle.None,
            ScrollBars  = RichTextBoxScrollBars.Vertical
        };
        Controls.Add(rtbLog);

        // ── Progress bar (orange custom) ──────────────────────────────────────
        pnlProgressBg = new Panel {
            Location  = new Point(20, 408),
            Size      = new Size(520, 14),
            BackColor = BG3
        };
        pnlProgressFill = new Panel {
            Location  = Point.Empty,
            Size      = new Size(0, 14),
            BackColor = ORANGE
        };
        pnlProgressBg.Controls.Add(pnlProgressFill);
        Controls.Add(pnlProgressBg);

        lblPct = new Label {
            Text      = "",
            ForeColor = DIM,
            Font      = new Font("Segoe UI", 8f),
            Location  = new Point(22, 426),
            AutoSize  = true
        };
        Controls.Add(lblPct);

        // ── Buttons ───────────────────────────────────────────────────────────
        btnAction = new Button {
            Text      = "  Installieren",
            Size      = new Size(165, 42),
            Location  = new Point(247, 466),
            BackColor = ORANGE,
            ForeColor = Color.FromArgb(15, 15, 15),
            FlatStyle = FlatStyle.Flat,
            Font      = new Font("Segoe UI", 10f, FontStyle.Bold)
        };
        btnAction.FlatAppearance.BorderSize = 0;
        btnAction.Click += OnActionClick;
        Controls.Add(btnAction);

        btnCancel = new Button {
            Text      = "Abbrechen",
            Size      = new Size(110, 42),
            Location  = new Point(430, 466),
            BackColor = BG3,
            ForeColor = GRAY,
            FlatStyle = FlatStyle.Flat
        };
        btnCancel.FlatAppearance.BorderSize = 0;
        btnCancel.Click += (s, e) => Close();
        Controls.Add(btnCancel);
    }

    // ── Welcome screen ────────────────────────────────────────────────────────
    void ShowWelcome()
    {
        Log("Willkommen beim Studforge Installations-Assistenten.", WHITE);
        Log(" ", GRAY);
        Log("Was wird installiert:", GRAY);
        Log("  · Python 3.11   (falls noch nicht vorhanden)", DIM);
        Log("  · Flask + PyWebView", DIM);
        Log("  · Studforge App-Dateien", DIM);
        Log("  · Desktop-Verknüpfung mit Icon", DIM);
        Log(" ", GRAY);
        Log("Klicke \"Installieren\" um zu starten.", GRAY);
    }

    // ── Button handler ────────────────────────────────────────────────────────
    void OnActionClick(object sender, EventArgs e)
    {
        if (installDone)
        {
            // Launch the app after successful install
            string python = FindPython();
            if (python != null)
            {
                string pw = python.Replace("python.exe", "pythonw.exe");
                if (!File.Exists(pw)) pw = python;
                Process.Start(pw,
                    "\"" + Path.Combine(INSTALL_DIR, "main.py") + "\"");
            }
            Close();
            return;
        }

        btnAction.Enabled = false;
        btnCancel.Enabled = false;
        rtbLog.Clear();

        new Thread(RunInstall) { IsBackground = true }.Start();
    }

    // ── Installation logic (background thread) ────────────────────────────────
    void RunInstall()
    {
        try
        {
            // ── 1. Python ─────────────────────────────────────────────────────
            Log("● Python wird gesucht ...", WHITE);
            SetStatus("Python suchen ...");
            SetProgress(5);

            string python = FindPython();
            if (python != null)
            {
                Log("  ✓ Gefunden: " + python, GREEN);
            }
            else
            {
                Log("  Nicht gefunden — Python 3.11 wird heruntergeladen ...", GRAY);
                SetProgress(8);
                string inst = Path.Combine(Path.GetTempPath(), "python-3.11.9-amd64.exe");

                SetStatus("Python herunterladen ...");
                using (var wc = new WebClient())
                    wc.DownloadFile(PYTHON_URL, inst);

                Log("  Python-Installer wird ausgeführt (bitte warten) ...", GRAY);
                SetStatus("Python installieren ...");
                var proc = Process.Start(new ProcessStartInfo(inst,
                    "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1")
                    { UseShellExecute = false });
                proc.WaitForExit();

                try { File.Delete(inst); } catch { }
                if (proc.ExitCode != 0)
                    throw new Exception("Python-Exit-Code: " + proc.ExitCode);

                python = FindPython();
                if (python == null)
                    throw new Exception("Python nach Installation nicht gefunden.");

                Log("  ✓ Python installiert: " + python, GREEN);
            }
            SetProgress(22);

            // ── 2. Download ───────────────────────────────────────────────────
            Log("● App wird von GitHub geladen ...", WHITE);
            SetStatus("App herunterladen ...");

            if (Directory.Exists(TEMP_DIR)) Directory.Delete(TEMP_DIR, true);
            Directory.CreateDirectory(TEMP_DIR);

            string zipPath = Path.Combine(TEMP_DIR, "studforge.zip");
            using (var wc = new WebClient())
                wc.DownloadFile(GITHUB_ZIP, zipPath);

            Log("  ✓ Download abgeschlossen", GREEN);
            SetProgress(45);

            // ── 3. Extract ────────────────────────────────────────────────────
            Log("● Dateien werden entpackt ...", WHITE);
            SetStatus("Entpacken ...");

            RunCmd("powershell",
                "-NoProfile -ExecutionPolicy Bypass -Command " +
                "\"Expand-Archive -Path '" + zipPath + "' " +
                "-DestinationPath '" + TEMP_DIR + "' -Force\"");

            string[] subdirs = Directory.GetDirectories(TEMP_DIR);
            if (subdirs.Length == 0)
                throw new Exception("Entpackter Ordner nicht gefunden.");

            if (Directory.Exists(INSTALL_DIR)) Directory.Delete(INSTALL_DIR, true);
            CopyDir(subdirs[0], INSTALL_DIR);

            Log("  ✓ Installiert in: " + INSTALL_DIR, GREEN);
            SetProgress(62);

            // ── 4. Pip packages ───────────────────────────────────────────────
            Log("● Flask & PyWebView werden installiert ...", WHITE);
            SetStatus("Pakete installieren ...");

            RunCmd(python, "-m pip install flask pywebview --quiet");

            Log("  ✓ Pakete installiert", GREEN);
            SetProgress(78);

            // ── 5. Icon ───────────────────────────────────────────────────────
            Log("● App-Icon wird generiert ...", WHITE);
            SetStatus("Icon generieren ...");

            RunCmd(python, "\"" + Path.Combine(INSTALL_DIR, "icon.py") + "\"");

            Log("  ✓ Icon erstellt", GREEN);
            SetProgress(90);

            // ── 6. Desktop shortcut ───────────────────────────────────────────
            Log("● Desktop-Verknüpfung wird erstellt ...", WHITE);
            SetStatus("Verknüpfung erstellen ...");

            string pythonw = python.Replace("python.exe", "pythonw.exe");
            if (!File.Exists(pythonw)) pythonw = python;
            CreateShortcut(pythonw, INSTALL_DIR);

            Log("  ✓ Verknüpfung auf dem Desktop erstellt", GREEN);
            SetProgress(100);

            // ── Done ──────────────────────────────────────────────────────────
            Log(" ", GRAY);
            Log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", ORANGE);
            Log("  Studforge wurde erfolgreich installiert!", GREEN);
            Log("  Klicke \"Starten\" oder nutze die Desktop-Verknüpfung.", GRAY);
            Log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", ORANGE);

            SetStatus("Installation abgeschlossen.");

            Invoke((Action)(() => {
                installDone       = true;
                btnAction.Text    = "  Starten  ▶";
                btnAction.Enabled = true;
                btnCancel.Text    = "Schliessen";
                btnCancel.Enabled = true;
            }));
        }
        catch (Exception ex)
        {
            Log(" ", GRAY);
            Log("  ✗ Fehler: " + ex.Message, RED);
            SetStatus("Installation fehlgeschlagen.");
            Invoke((Action)(() => {
                btnAction.Text    = "  Wiederholen";
                btnAction.Enabled = true;
                btnCancel.Enabled = true;
            }));
        }
        finally
        {
            try { if (Directory.Exists(TEMP_DIR)) Directory.Delete(TEMP_DIR, true); } catch { }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    static string FindPython()
    {
        string la = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] paths = {
            la + @"\Programs\Python\Python311\python.exe",
            la + @"\Programs\Python\Python312\python.exe",
            la + @"\Programs\Python\Python313\python.exe",
            la + @"\Programs\Python\Python310\python.exe",
            la + @"\Programs\Python\Python39\python.exe",
            @"C:\Python311\python.exe",
            @"C:\Python312\python.exe",
            @"C:\Python310\python.exe",
        };
        foreach (string p in paths)
            if (File.Exists(p)) return p;
        return null;
    }

    void Log(string msg, Color col)
    {
        if (rtbLog.InvokeRequired) { rtbLog.Invoke((Action)(() => Log(msg, col))); return; }
        rtbLog.SelectionStart  = rtbLog.TextLength;
        rtbLog.SelectionLength = 0;
        rtbLog.SelectionColor  = col;
        rtbLog.AppendText(msg + "\n");
        rtbLog.ScrollToCaret();
    }

    void SetStatus(string msg)
    {
        if (lblStatus.InvokeRequired) { lblStatus.Invoke((Action)(() => SetStatus(msg))); return; }
        lblStatus.Text = msg;
    }

    void SetProgress(int pct)
    {
        if (pnlProgressFill.InvokeRequired)
        { pnlProgressFill.Invoke((Action)(() => SetProgress(pct))); return; }
        pnlProgressFill.Width = (int)(pnlProgressBg.Width * pct / 100.0);
        lblPct.Text = pct + " %";
    }

    static void RunCmd(string exe, string args)
    {
        var p = Process.Start(new ProcessStartInfo(exe, args) {
            UseShellExecute        = false,
            CreateNoWindow         = true,
            RedirectStandardOutput = true,
            RedirectStandardError  = true
        });
        p.WaitForExit();
    }

    static void CopyDir(string src, string dst)
    {
        Directory.CreateDirectory(dst);
        foreach (string f in Directory.GetFiles(src))
            File.Copy(f, Path.Combine(dst, Path.GetFileName(f)), true);
        foreach (string d in Directory.GetDirectories(src))
            CopyDir(d, Path.Combine(dst, Path.GetFileName(d)));
    }

    static void CreateShortcut(string pythonw, string appDir)
    {
        string mainPy  = Path.Combine(appDir, "main.py");
        string icoPath = Path.Combine(appDir, "icon.ico");
        string desktop = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
        string vbs     = Path.Combine(Path.GetTempPath(), "sf_sc.vbs");

        File.WriteAllText(vbs,
            "Set ws=CreateObject(\"WScript.Shell\")\n" +
            "Set sc=ws.CreateShortcut(\"" + desktop + "\\Studforge.lnk\")\n" +
            "sc.TargetPath=\"" + pythonw + "\"\n" +
            "sc.Arguments=Chr(34)&\"" + mainPy + "\"&Chr(34)\n" +
            "sc.WorkingDirectory=\"" + appDir + "\"\n" +
            "sc.IconLocation=\"" + icoPath + "\"\n" +
            "sc.Description=\"Studforge 3D Manufaktur\"\n" +
            "sc.Save");

        Process.Start(new ProcessStartInfo("wscript.exe", "\"" + vbs + "\"")
            { UseShellExecute = false, CreateNoWindow = true }).WaitForExit();

        try { File.Delete(vbs); } catch { }
    }
}
