#!/usr/bin/env python3
# File        : midi_loopback.py
# Author      : Nathan Cohen (drafted with AI assistance, Anthropic Claude)
# Revision    : 1, 2026-11-22
# Project     : ECEN 5613 final project, test scripts
# Description : Loopback test of the KB2040 USB-MIDI bridge (A2, firmware/kb2040/code.py).
#               Finds the "CircuitPython" MIDI endpoint, sends notes and pitch bends to it,
#               reads what comes back and reports MATCH or MISMATCH for each trial.
#               Setup: KB2040 on USB, its TX pin jumpered to its RX pin, nothing else on
#               them (MVP_Bench_Tests.md stage E4). Remove the jumper afterwards.
#               macOS only: it calls CoreMIDI through ctypes, so it needs no packages.
#                 python3 -I tools/midi_loopback.py
# Status      : Run once on 2026-11-22: all three trials matched (6, 120 and 63 bytes)
# Leveraged   : Apple CoreMIDI C API (MIDIClientCreate, MIDIInputPortCreate, MIDISend,
#               MIDIPacketList). A first version crashed because ctypes passed the
#               64-bit CFString pointers as 32-bit ints; every call that takes a
#               pointer now declares its argtypes.
import ctypes, ctypes.util, time, threading
cm = ctypes.CDLL(ctypes.util.find_library('CoreMIDI'))
cf = ctypes.CDLL(ctypes.util.find_library('CoreFoundation'))
U32 = ctypes.c_uint32
cf.CFStringCreateWithCString.restype = ctypes.c_void_p
cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, U32]
cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, U32]
cm.MIDIGetNumberOfSources.restype = ctypes.c_ulong
cm.MIDIGetNumberOfDestinations.restype = ctypes.c_ulong
cm.MIDIGetSource.restype = U32;       cm.MIDIGetSource.argtypes = [ctypes.c_ulong]
cm.MIDIGetDestination.restype = U32;  cm.MIDIGetDestination.argtypes = [ctypes.c_ulong]
cm.MIDIObjectGetStringProperty.argtypes = [U32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
UTF8 = 0x08000100
def cfs(s): return cf.CFStringCreateWithCString(None, s.encode(), UTF8)
KEY = cfs("name")
def name(o):
    s = ctypes.c_void_p()
    if cm.MIDIObjectGetStringProperty(o, KEY, ctypes.byref(s)) != 0: return "?"
    b = ctypes.create_string_buffer(256); cf.CFStringGetCString(s, b, 256, UTF8)
    return b.value.decode()
src = next((cm.MIDIGetSource(i) for i in range(cm.MIDIGetNumberOfSources()) if "CircuitPython" in name(cm.MIDIGetSource(i))), None)
dst = next((cm.MIDIGetDestination(i) for i in range(cm.MIDIGetNumberOfDestinations()) if "CircuitPython" in name(cm.MIDIGetDestination(i))), None)
if src is None or dst is None:
    raise SystemExit("KB2040 MIDI endpoint not found")

got = bytearray(); lock = threading.Lock()
READPROC = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
def on_read(pktlist, _a, _b):
    n = ctypes.cast(pktlist, ctypes.POINTER(U32))[0]
    p = pktlist + 4
    for _ in range(n):
        ln = ctypes.cast(p + 8, ctypes.POINTER(ctypes.c_uint16))[0]
        data = ctypes.string_at(p + 10, ln)
        with lock: got.extend(data)
        p = (p + 10 + ln + 3) & ~3      # packets are 4-byte aligned on arm64
cb = READPROC(on_read)
cb_ptr = ctypes.cast(cb, ctypes.c_void_p)

P=ctypes.c_void_p
cm.MIDIClientCreate.argtypes = [P, P, P, ctypes.POINTER(U32)]
cm.MIDIInputPortCreate.argtypes = [U32, P, P, P, ctypes.POINTER(U32)]
cm.MIDIOutputPortCreate.argtypes = [U32, P, ctypes.POINTER(U32)]
cm.MIDIPortConnectSource.argtypes = [U32, U32, P]
cm.MIDIPacketListInit.argtypes = [P]
client = U32(); inp = U32(); out = U32()
assert cm.MIDIClientCreate(cfs("loopback"), None, None, ctypes.byref(client)) == 0
assert cm.MIDIInputPortCreate(client, cfs("in"), cb_ptr, None, ctypes.byref(inp)) == 0
assert cm.MIDIOutputPortCreate(client, cfs("out"), ctypes.byref(out)) == 0
assert cm.MIDIPortConnectSource(inp, src, None) == 0

cm.MIDIPacketListInit.restype = ctypes.c_void_p
cm.MIDIPacketListAdd.restype = ctypes.c_void_p
cm.MIDIPacketListAdd.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_ulong, ctypes.c_char_p]
cm.MIDISend.argtypes = [U32, U32, ctypes.c_void_p]
def send(b):
    buf = ctypes.create_string_buffer(1024)
    pkt = cm.MIDIPacketListInit(buf)
    cm.MIDIPacketListAdd(buf, 1024, pkt, 0, len(b), bytes(b))
    assert cm.MIDISend(out, dst, buf) == 0

def trial(label, msgs, wait):
    with lock: got.clear()
    sent = b"".join(bytes(m) for m in msgs)
    t0 = time.time()
    for m in msgs:
        send(m)
        time.sleep(0.004)
    deadline = time.time() + wait
    while time.time() < deadline:
        with lock:
            if len(got) >= len(sent): break
        time.sleep(0.01)
    dt = (time.time() - t0) * 1000
    with lock: r = bytes(got)
    print(f"{label}: sent {len(sent)} bytes, got {len(r)} back in {dt:.0f} ms -> {'MATCH' if r == sent else 'MISMATCH'}")
    if r != sent:
        print("   sent:", sent.hex(" "));  print("   got: ", r.hex(" "))

trial("single note on/off", [(0x90, 60, 100), (0x80, 60, 0)], 2)
trial("burst of 40 messages", [(0x90, 40 + i, 90) for i in range(20)] + [(0x80, 40 + i, 0) for i in range(20)], 4)
trial("fader-style pitch bends", [(0xE0, (v & 0x7F), (v >> 7) & 0x7F) for v in range(0, 16384, 819)], 4)
