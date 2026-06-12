using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;
using System.Runtime.InteropServices;

class Launcher
{
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();

    [STAThread]
    static void Main()
    {
        try { SetProcessDPIAware(); } catch { }

        string appDir = Path.GetDirectoryName(
            System.Reflection.Assembly.GetExecutingAssembly().Location);

        string la = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] candidates = {
            la + @"\Programs\Python\Python311\pythonw.exe",
            la + @"\Programs\Python\Python312\pythonw.exe",
            la + @"\Programs\Python\Python313\pythonw.exe",
            la + @"\Programs\Python\Python310\pythonw.exe",
            la + @"\Programs\Python\Python39\pythonw.exe",
            @"C:\Python311\pythonw.exe",
            @"C:\Python312\pythonw.exe",
            @"C:\Python310\pythonw.exe",
        };

        string pythonw = null;
        foreach (string p in candidates)
            if (File.Exists(p)) { pythonw = p; break; }

        if (pythonw == null)
        {
            MessageBox.Show(
                "Python wurde nicht gefunden.\nBitte Studforge neu installieren.",
                "Studforge", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        string mainPy = Path.Combine(appDir, "main.py");
        Process.Start(new ProcessStartInfo(pythonw, "\"" + mainPy + "\"")
        {
            WorkingDirectory  = appDir,
            UseShellExecute   = false
        });
    }
}
