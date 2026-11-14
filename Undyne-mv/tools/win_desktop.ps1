# Lift the desktop's pieces off this Windows 11 machine (README 场景 · 桌面; user 2026-10-19: icons are
# Windows' own defaults): every icon exactly as the shell draws it, at each size the desktop, the taskbar
# and the title bar ask for, plus the metrics the desktop really uses (its icon grid, the icon-title and
# caption fonts).
#
#   pwsh tools/win_desktop.ps1            -> asset/desktop/<name>_<size>.png, work/desk/metrics.txt
#
# Icons come from IShellItemImageFactory (what Explorer itself draws: files, folders, exes, the shell's
# own folders) or from a DLL's icon resource by id (PrivateExtractIcons); both are saved with straight
# alpha. The cursors (.cur) are converted by tools/win_cursors.py.
param([string]$Out = 'asset/desktop')
$ErrorActionPreference = 'Stop'

Add-Type -ReferencedAssemblies System.Drawing.Common, System.Drawing.Primitives -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text;

public static class WinDesk {
  [ComImport, Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IShellItemImageFactory { [PreserveSig] int GetImage(SIZE size, int flags, out IntPtr phbm); }
  [StructLayout(LayoutKind.Sequential)] struct SIZE { public int cx, cy; }
  [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
  static extern void SHCreateItemFromParsingName(string path, IntPtr pbc, [MarshalAs(UnmanagedType.LPStruct)] Guid riid,
    [MarshalAs(UnmanagedType.Interface)] out IShellItemImageFactory ppv);
  [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr h);
  [DllImport("gdi32.dll")] static extern int GetObject(IntPtr h, int c, IntPtr buf);
  [DllImport("gdi32.dll")] static extern int GetDIBits(IntPtr hdc, IntPtr hbm, uint start, uint lines, byte[] bits, ref BITMAPINFOHEADER bi, uint usage);
  [DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr h);
  [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr h, IntPtr dc);
  [DllImport("user32.dll")] static extern bool GetIconInfo(IntPtr h, out ICONINFO ii);
  [DllImport("user32.dll")] static extern bool DestroyIcon(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  static extern uint PrivateExtractIcons(string file, int index, int cx, int cy, IntPtr[] icons, int[] ids, uint n, uint flags);
  [StructLayout(LayoutKind.Sequential)] struct ICONINFO { public bool fIcon; public int x, y; public IntPtr mask, color; }
  [StructLayout(LayoutKind.Sequential)] struct BITMAPINFOHEADER {
    public int biSize, biWidth, biHeight; public short biPlanes, biBitCount;
    public int biCompression, biSizeImage, biXPelsPerMeter, biYPelsPerMeter, biClrUsed, biClrImportant; }

  // 32-bit BGRA rows, top-down -> PNG with straight alpha (pre: the rows are premultiplied)
  static void Save(byte[] px, int w, int h, bool pre, string png) {
    bool any = false;
    for (int i = 3; i < px.Length; i += 4) if (px[i] != 0) { any = true; break; }
    var bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
    var bd = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
    var o = new byte[bd.Stride * h];
    for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
      int s = (y * w + x) * 4, d = y * bd.Stride + x * 4;
      int b = px[s], g = px[s + 1], r = px[s + 2], a = any ? px[s + 3] : 255;
      if (pre && a > 0 && a < 255) { r = Math.Min(255, r * 255 / a); g = Math.Min(255, g * 255 / a); b = Math.Min(255, b * 255 / a); }
      if (a == 0) { r = g = b = 0; }
      o[d] = (byte)b; o[d + 1] = (byte)g; o[d + 2] = (byte)r; o[d + 3] = (byte)a;
    }
    Marshal.Copy(o, 0, bd.Scan0, o.Length);
    bmp.UnlockBits(bd);
    bmp.Save(png, ImageFormat.Png);
    bmp.Dispose();
  }
  static byte[] Bits(IntPtr hbm, out int w, out int h) {
    var bm = Marshal.AllocHGlobal(64);
    GetObject(hbm, 32, bm);
    w = Marshal.ReadInt32(bm, 4); h = Math.Abs(Marshal.ReadInt32(bm, 8));
    Marshal.FreeHGlobal(bm);
    var bi = new BITMAPINFOHEADER { biSize = 40, biWidth = w, biHeight = -h, biPlanes = 1, biBitCount = 32 };
    var px = new byte[w * h * 4];
    IntPtr dc = GetDC(IntPtr.Zero);
    GetDIBits(dc, hbm, 0, (uint)h, px, ref bi, 0);
    ReleaseDC(IntPtr.Zero, dc);
    return px;
  }
  // what the shell draws for a path / parsing name (flags: 0x4 icon only, 0x1 bigger ok ...)
  public static void Shell(string path, int size, string png, int flags) {
    IShellItemImageFactory f;
    SHCreateItemFromParsingName(path, IntPtr.Zero, typeof(IShellItemImageFactory).GUID, out f);
    IntPtr hbm;
    int hr = f.GetImage(new SIZE { cx = size, cy = size }, flags, out hbm);
    if (hr != 0) throw new Exception("GetImage 0x" + hr.ToString("X") + " " + path);
    int w, h; var px = Bits(hbm, out w, out h);
    DeleteObject(hbm);
    // (the factory's bitmap is premultiplied unless a colour channel says otherwise)
    bool pre = true;
    for (int i = 0; i < px.Length; i += 4) if (px[i] > px[i + 3] || px[i + 1] > px[i + 3] || px[i + 2] > px[i + 3]) { pre = false; break; }
    Save(px, w, h, pre, png);
    Marshal.FinalReleaseComObject(f);
  }
  // an icon resource in a module: index >= 0 by position, < 0 by resource id
  public static void Res(string file, int index, int size, string png) {
    var icons = new IntPtr[1]; var ids = new int[1];
    uint n = PrivateExtractIcons(file, index, size, size, icons, ids, 1, 0);
    if (n == 0 || icons[0] == IntPtr.Zero) throw new Exception("no icon " + file + "," + index);
    ICONINFO ii; GetIconInfo(icons[0], out ii);
    int w, h; var px = Bits(ii.color, out w, out h);
    DeleteObject(ii.color); DeleteObject(ii.mask); DestroyIcon(icons[0]);
    Save(px, w, h, false, png);
  }

  // ---- the desktop's own metrics
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr FindWindow(string c, string n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string n);
  [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, int m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("kernel32.dll")] static extern IntPtr OpenProcess(uint a, bool i, uint pid);
  [DllImport("kernel32.dll")] static extern IntPtr VirtualAllocEx(IntPtr p, IntPtr a, int n, uint t, uint pr);
  [DllImport("kernel32.dll")] static extern bool VirtualFreeEx(IntPtr p, IntPtr a, int n, uint t);
  [DllImport("kernel32.dll")] static extern bool WriteProcessMemory(IntPtr p, IntPtr a, byte[] b, int n, out IntPtr w);
  [DllImport("kernel32.dll")] static extern bool ReadProcessMemory(IntPtr p, IntPtr a, byte[] b, int n, out IntPtr r);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern bool SystemParametersInfo(uint a, uint b, IntPtr p, uint f);
  [DllImport("user32.dll")] static extern int GetSystemMetrics(int i);

  static IntPtr DesktopList() {
    IntPtr def = FindWindowEx(FindWindow("Progman", null), IntPtr.Zero, "SHELLDLL_DefView", null);
    for (IntPtr w = IntPtr.Zero; def == IntPtr.Zero && (w = FindWindowEx(IntPtr.Zero, w, "WorkerW", null)) != IntPtr.Zero;)
      def = FindWindowEx(w, IntPtr.Zero, "SHELLDLL_DefView", null);
    return FindWindowEx(def, IntPtr.Zero, "SysListView32", null);
  }
  static string Font(IntPtr p, int off) {
    int h = Marshal.ReadInt32(p, off), wt = Marshal.ReadInt32(p, off + 16);
    string face = Marshal.PtrToStringUni(p + off + 28);
    return face + " h=" + h + " weight=" + wt;
  }
  public static string Metrics() {
    var sb = new StringBuilder();
    IntPtr lv = DesktopList();
    long sp = (long)SendMessage(lv, 0x1033, IntPtr.Zero, IntPtr.Zero);       // LVM_GETITEMSPACING
    int n = (int)SendMessage(lv, 0x1004, IntPtr.Zero, IntPtr.Zero);          // LVM_GETITEMCOUNT
    sb.AppendLine("desktop listview: spacing " + (sp & 0xFFFF) + " x " + ((sp >> 16) & 0xFFFF) + ", items " + n);
    uint pid; GetWindowThreadProcessId(lv, out pid);
    IntPtr pr = OpenProcess(0x0008 | 0x0010 | 0x0020, false, pid);
    IntPtr mem = VirtualAllocEx(pr, IntPtr.Zero, 64, 0x3000, 0x04);
    var buf = new byte[16]; IntPtr io;
    for (int i = 0; i < Math.Min(n, 16); i++) {
      var line = new StringBuilder("  item " + i + ":");
      foreach (int code in new[] { 0, 1, 2 }) {                              // LVIR_BOUNDS, ICON, LABEL
        var r = new byte[16]; BitConverter.GetBytes(code).CopyTo(r, 0);
        WriteProcessMemory(pr, mem, r, 16, out io);
        SendMessage(lv, 0x100E, (IntPtr)i, mem);                              // LVM_GETITEMRECT
        ReadProcessMemory(pr, mem, buf, 16, out io);
        line.Append(new[] { " bounds", " icon", " label" }[code] + " " + BitConverter.ToInt32(buf, 0) + "," + BitConverter.ToInt32(buf, 4) + "-" + BitConverter.ToInt32(buf, 8) + "," + BitConverter.ToInt32(buf, 12));
      }
      sb.AppendLine(line.ToString());
    }
    VirtualFreeEx(pr, mem, 0, 0x8000); CloseHandle(pr);
    IntPtr lf = Marshal.AllocHGlobal(512);
    SystemParametersInfo(0x001F, 92, lf, 0);                                  // SPI_GETICONTITLELOGFONT
    sb.AppendLine("icon title font: " + Font(lf, 0));
    Marshal.WriteInt32(lf, 0, 504);
    SystemParametersInfo(0x0029, 504, lf, 0);                                 // SPI_GETNONCLIENTMETRICS
    // (NONCLIENTMETRICSW: cbSize, iBorderWidth, iScrollWidth, iScrollHeight, iCaptionWidth @16,
    // iCaptionHeight @20, lfCaptionFont @24, iSmCaption* @116, lfSmCaptionFont @124, iMenu* @216,
    // lfMenuFont @224, lfStatusFont @316, lfMessageFont @408, iPaddedBorderWidth @500)
    sb.AppendLine("caption buttons: " + Marshal.ReadInt32(lf, 16) + " x " + Marshal.ReadInt32(lf, 20) + ", caption font " + Font(lf, 24) + ", padded border " + Marshal.ReadInt32(lf, 500));
    sb.AppendLine("menu / status / message font: " + Font(lf, 224) + " | " + Font(lf, 316) + " | " + Font(lf, 408));
    Marshal.FreeHGlobal(lf);
    sb.AppendLine("SM_CXICONSPACING " + GetSystemMetrics(38) + " SM_CYICONSPACING " + GetSystemMetrics(39) + " SM_CXFIXEDFRAME " + GetSystemMetrics(7) + " SM_CYCAPTION " + GetSystemMetrics(4) + " SM_CXPADDEDBORDER " + GetSystemMetrics(92));
    return sb.ToString();
  }
}
'@

New-Item -ItemType Directory -Force $Out | Out-Null
New-Item -ItemType Directory -Force 'work/desk' | Out-Null
$root = (Resolve-Path .).Path
$OutAbs = (Resolve-Path $Out).Path

# stand-ins on disk for the desktop's own files (a folder with something in it, an empty one, a .txt)
$tmp = [System.IO.Path]::GetFullPath((Join-Path $root 'work\desk\items'))
New-Item -ItemType Directory -Force "$tmp\full", "$tmp\empty" | Out-Null
if (-not (Test-Path "$tmp\full\x.txt")) { Set-Content "$tmp\full\x.txt" 'x' }
if (-not (Test-Path "$tmp\notes.txt")) { Set-Content "$tmp\notes.txt" 'x' }

$discord = Get-ChildItem "$env:LOCALAPPDATA/Discord" -Directory -Filter 'app-*' | Sort-Object Name | Select-Object -Last 1
$SHELL = [ordered]@{
  thispc      = '::{20D04FE0-3AEA-1069-A2D8-08002B30309D}'
  folder      = "$tmp\full"
  folderEmpty = "$tmp\empty"
  txt         = "$tmp\notes.txt"
  explorer    = 'C:\Windows\explorer.exe'
  edge        = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
  steam       = 'C:\Program Files (x86)\Steam\steam.exe'
  undertale   = 'D:\SteamLibrary\steamapps\common\Undertale\UNDERTALE.exe'
  obs         = 'C:\Program Files\obs-studio\bin\64bit\obs64.exe'
  discord     = (Join-Path $discord.FullName 'Discord.exe')
  notepad     = 'shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App'
}
$SIZES = 16, 20, 24, 32, 48, 256
foreach ($k in $SHELL.Keys) {
  foreach ($s in $SIZES) { [WinDesk]::Shell($SHELL[$k], $s, "$OutAbs/${k}_$s.png", 0x4) }
  "shell  $k"
}
# imageres.dll: the recycle bin (empty / full) and the shortcut arrow, by resource id
$RES = [ordered]@{ recycleEmpty = -55; recycleFull = -54; shortcut = -163 }
foreach ($k in $RES.Keys) {
  foreach ($s in $SIZES) { [WinDesk]::Res('C:\Windows\System32\imageres.dll', $RES[$k], $s, "$OutAbs/${k}_$s.png") }
  "res    $k"
}
[WinDesk]::Metrics() | Tee-Object -FilePath 'work/desk/metrics.txt'

# the wallpaper: Windows 11's own Bloom (the same picture as asset/Img0_(Windows_11).jpg, at its full
# 3840x2400), cropped the way "Fill" crops it for a 16:9 screen - 120 px off the top and the bottom
ffmpeg -v error -y -i 'C:/Windows/Web/Wallpaper/Windows/img0.jpg' -vf 'crop=3840:2160:0:120' -q:v 2 "$OutAbs/wallpaper.jpg"
"wallpaper " + (Get-Item "$OutAbs/wallpaper.jpg").Length
