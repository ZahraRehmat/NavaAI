using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows.Forms;
using System.Reflection;
[assembly: AssemblyTitle("NAVA AI")]
[assembly: AssemblyDescription("Hands-free Windows control")]
[assembly: AssemblyCompany("NAVA AI")]
[assembly: AssemblyProduct("NAVA AI")]
[assembly: AssemblyVersion("1.0.1.0")]
[assembly: AssemblyFileVersion("1.0.1.0")]
class Launcher {
    static string Quote(string value) {
        var s = new StringBuilder("\""); int slashes=0;
        foreach(char c in value) {
            if(c=='\\') { slashes++; continue; }
            if(c=='"') { s.Append('\\',slashes*2+1); s.Append(c); slashes=0; continue; }
            s.Append('\\',slashes);slashes=0;s.Append(c);
        }
        s.Append('\\',slashes*2);s.Append('"');return s.ToString();
    }
    [STAThread] static int Main(string[] args) {
        string root=AppDomain.CurrentDomain.BaseDirectory;
        try {
            string python=Path.Combine(root,"runtime","pythonw.exe");
            string script=Path.Combine(root,"installed_bootstrap.py");
            if(!File.Exists(python)||!File.Exists(script))throw new IOException("The NAVA AI installation is incomplete. Please run Setup again.");
            var start=new ProcessStartInfo(python,Quote(script));
            foreach(string arg in args)start.Arguments+=" "+Quote(arg);
            start.WorkingDirectory=root;start.UseShellExecute=false;start.CreateNoWindow=true;start.WindowStyle=ProcessWindowStyle.Hidden;
            start.EnvironmentVariables["PYTHONUTF8"]="1";
            start.EnvironmentVariables["PYTHONNOUSERSITE"]="1";
            start.EnvironmentVariables["PLAYWRIGHT_BROWSERS_PATH"]=Path.Combine(root,"browsers");
            start.EnvironmentVariables["TCL_LIBRARY"]=Path.Combine(root,"runtime","tcl","tcl8.6");
            start.EnvironmentVariables["TK_LIBRARY"]=Path.Combine(root,"runtime","tcl","tk8.6");
            bool wait=Array.Exists(args,x=>x=="--initialize"||x=="--self-test"||x=="--ui-smoke");
            using(Process child=Process.Start(start)) { if(wait){child.WaitForExit();return child.ExitCode;} }
            return 0;
        } catch(Exception error) {
            MessageBox.Show(error.Message,"NAVA AI",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;
        }
    }
}
