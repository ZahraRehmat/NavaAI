// Drawing-only UIAccess companion. No input injection, app control or shell commands.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

static class Native {
    [DllImport("kernel32.dll")] internal static extern IntPtr GetCurrentProcess();
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr p, uint a, out IntPtr t);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool GetTokenInformation(IntPtr t, int c, out int v, int n, out int r);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
    [DllImport("user32.dll")] internal static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int w, int height, uint flags);
    internal static bool HasUIAccess() {
        IntPtr token; if(!OpenProcessToken(GetCurrentProcess(), 8, out token)) return false;
        try { int value, read; return GetTokenInformation(token,26,out value,4,out read) && value!=0; }
        finally { CloseHandle(token); }
    }
}

static class Drawing {
    internal static Dictionary<string,object> Map(object value) { return (Dictionary<string,object>)value; }
    internal static float F(object value) { return Convert.ToSingle(value); }
    internal static string S(Dictionary<string,object> item,string key) { return item.ContainsKey(key)?Convert.ToString(item[key]):""; }
    internal static float[] Numbers(object value) {
        var list=new List<float>(); foreach(object n in (IEnumerable)value) list.Add(F(n)); return list.ToArray();
    }
    static Color Colour(string value) { return String.IsNullOrEmpty(value)?Color.Transparent:ColorTranslator.FromHtml(value); }
    internal static void Paint(Graphics g, IEnumerable commands) {
        g.SmoothingMode=SmoothingMode.None;
        foreach(object obj in commands) {
            var op=Map(obj); var p=Numbers(op["coords"]); string kind=S(op,"kind");
            if(kind=="text") {
                using(var font=new Font("Segoe UI",F(op["font_size"]),FontStyle.Bold,GraphicsUnit.Pixel))
                using(var brush=new SolidBrush(Colour(S(op,"fill")))) {
                    string text=S(op,"text"); float x=p[0],y=p[1];
                    var format=StringFormat.GenericTypographic;
                    if(S(op,"anchor")=="center") {var size=g.MeasureString(text,font,1000,format);x-=size.Width/2;y-=size.Height/2;}
                    g.DrawString(text,font,brush,x,y,format);
                }
                continue;
            }
            string stroke=S(op,kind=="line"?"fill":"outline"); float width=op.ContainsKey("width")?F(op["width"]):1;
            if(kind=="line") {
                using(var pen=new Pen(Colour(stroke),width)) for(int i=0;i+3<p.Length;i+=2) g.DrawLine(pen,p[i],p[i+1],p[i+2],p[i+3]);
                continue;
            }
            if(p.Length<4) continue;
            var box=new RectangleF(p[0],p[1],Math.Max(0,p[2]-p[0]),Math.Max(0,p[3]-p[1]));
            if(!String.IsNullOrEmpty(S(op,"fill"))) using(var brush=new SolidBrush(Colour(S(op,"fill")))) {
                if(kind=="oval") g.FillEllipse(brush,box); else g.FillRectangle(brush,box);
            }
            if(!String.IsNullOrEmpty(stroke)) using(var pen=new Pen(Colour(stroke),width)) {
                if(kind=="oval") g.DrawEllipse(pen,box); else g.DrawRectangle(pen,box.X,box.Y,box.Width,box.Height);
            }
        }
    }
}

sealed class Layer : Form {
    IEnumerable commands=new object[0];
    public Layer() {
        Text="Gwen Doer Accessibility Grid";FormBorderStyle=FormBorderStyle.None;
        ShowInTaskbar=false;TopMost=true;StartPosition=FormStartPosition.Manual;
        BackColor=Color.FromArgb(1,2,3);TransparencyKey=BackColor;DoubleBuffered=true;
        AutoScaleMode=AutoScaleMode.None;
    }
    protected override bool ShowWithoutActivation { get {return true;} }
    protected override CreateParams CreateParams {get {var p=base.CreateParams;p.ExStyle|=0x080800a0;return p;}}
    protected override void OnPaint(PaintEventArgs e) {Drawing.Paint(e.Graphics,commands);}
    internal void UpdateFrame(Dictionary<string,object> area) {
        var b=Drawing.Numbers(area["bounds"]);Bounds=new Rectangle((int)b[0],(int)b[1],(int)(b[2]-b[0]),(int)(b[3]-b[1]));
        commands=(IEnumerable)area["commands"];if(!Visible) Show();Invalidate();
        Native.SetWindowPos(Handle,new IntPtr(-1),0,0,0,0,0x1|0x2|0x10);
    }
}

sealed class OverlayApp : ApplicationContext {
    readonly Control dispatcher=new Control(); readonly List<Layer> layers=new List<Layer>();
    internal OverlayApp(string pipeName) {
        IntPtr handle=dispatcher.Handle;
        var thread=new Thread(delegate(){Read(pipeName);});thread.IsBackground=true;thread.Start();
    }
    void Apply(Dictionary<string,object> frame) {
        if(!Convert.ToBoolean(frame["active"])) {foreach(var l in layers) l.Hide();return;}
        var areas=new List<Dictionary<string,object>>();foreach(object a in (IEnumerable)frame["areas"]) areas.Add(Drawing.Map(a));
        if(areas.Count>16) throw new InvalidDataException("Too many displays");
        while(layers.Count<areas.Count) layers.Add(new Layer());
        for(int i=0;i<layers.Count;i++) {if(i<areas.Count) layers[i].UpdateFrame(areas[i]);else layers[i].Hide();}
    }
    void Read(string name) {
        try {
            var security=new PipeSecurity();security.SetAccessRuleProtection(true,false);
            security.AddAccessRule(new PipeAccessRule(WindowsIdentity.GetCurrent().User,PipeAccessRights.FullControl,AccessControlType.Allow));
            using(var pipe=new NamedPipeServerStream(name,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.None,65536,65536,security)) {
                pipe.WaitForConnection();
                var utf8=new UTF8Encoding(false);var writer=new StreamWriter(pipe,utf8);writer.AutoFlush=true;writer.WriteLine("READY UIACCESS=1");
                var reader=new StreamReader(pipe,utf8);var serializer=new JavaScriptSerializer();serializer.MaxJsonLength=6000000;
                string line;while((line=reader.ReadLine())!=null) {
                    if(line.Length>6000000) throw new InvalidDataException("Frame too large");
                    var frame=serializer.Deserialize<Dictionary<string,object>>(line);
                    dispatcher.BeginInvoke((Action)delegate(){try {Apply(frame);} catch {ExitThread();}});
                }
            }
        } catch {} finally {try {dispatcher.BeginInvoke((Action)delegate(){ExitThread();});}catch{}}
    }
    protected override void ExitThreadCore() {foreach(var l in layers) l.Close();dispatcher.Dispose();base.ExitThreadCore();}
}

static class Program {
    [STAThread] static void Main(string[] args) {
        if(args.Length==2 && args[0]=="--render-test") {
            using(var bitmap=new Bitmap(400,200)) using(var g=Graphics.FromImage(bitmap)) {
                g.Clear(Color.FromArgb(1,2,3));
                var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(Console.In.ReadToEnd());
                Drawing.Paint(g,(IEnumerable)data["commands"]);bitmap.Save(args[1]);
            }
            return;
        }
        if(args.Length!=1 || !args[0].StartsWith("GwenOverlay-") || !Native.HasUIAccess()) return;
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new OverlayApp(args[0]));
    }
}
