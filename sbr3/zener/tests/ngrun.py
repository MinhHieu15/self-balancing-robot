"""Run an ngspice netlist through KiCad's ngspice.dll (shared-library API) and print its output."""
import ctypes, os, sys, time
KBIN = r"C:\Program Files\KiCad\10.0\bin"
os.add_dll_directory(KBIN)
os.environ["PATH"] = KBIN + os.pathsep + os.environ["PATH"]
ng = ctypes.CDLL(os.path.join(KBIN, "ngspice.dll"))
SendChar = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
SendStat = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
Exit = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
BG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
lines = []
def on_char(s, i, u):
    t = s.decode(errors="replace")
    if t.startswith("stdout "): t = t[7:]
    elif t.startswith("stderr "): t = "ERR " + t[7:]
    lines.append(t); print(t, flush=True); return 0
def on_stat(s, i, u): return 0
def on_exit(st, unload, q, i, u): return 0
def on_bg(r, i, u): return 0
cbs = (SendChar(on_char), SendStat(on_stat), Exit(on_exit), BG(on_bg))
ng.ngSpice_Init(cbs[0], cbs[1], cbs[2], None, None, cbs[3], None)
cir = os.path.abspath(sys.argv[1])
os.chdir(os.path.dirname(cir))
ng.ngSpice_Command(("source " + cir.replace("\\", "/")).encode())
