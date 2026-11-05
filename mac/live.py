#!/usr/bin/python3 -I
"""The phone's live console over USB, and the restart order, driven by the log rather than a timer.

  mac/live.py LOGFILE [--until REGEX]... [--grace SECONDS] [--wait SECONDS]

Appends everything the phone sends to LOGFILE. Sends the restart order (the phone flushes its log and
returns to Android) when a line matches an --until regex, GRACE seconds later, or when the file
LOGFILE.reboot appears. Ends when the port goes away. The kernel's pandora_reboot_after stays as a net.
"""
import glob, os, re, select, sys, termios, time, zlib

def frame(session, seq, verb):
    head = "SXNU1 %016x %08x %s" % (session, seq, verb)
    return ("%s %08x\n" % (head, zlib.crc32(head.encode()) & 0xffffffff)).encode()

def main():
    a = sys.argv[1:]
    log, until, grace, wait = a[0], [], 3.0, 600.0
    i = 1
    while i < len(a):
        if a[i] == "--until": until.append(re.compile(a[i + 1].encode()))
        elif a[i] == "--grace": grace = float(a[i + 1])
        elif a[i] == "--wait": wait = float(a[i + 1])
        else: sys.exit("unknown option " + a[i])
        i += 2
    end = time.time() + wait
    port = None
    while time.time() < end:
        p = glob.glob("/dev/cu.usbmodem*")
        if p: port = p[0]; break
        time.sleep(0.25)
    if not port: sys.exit("no USB console")
    time.sleep(0.2)
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    t = termios.tcgetattr(fd)
    t[0] = 0; t[1] = 0; t[3] = 0; t[6][termios.VMIN] = 0; t[6][termios.VTIME] = 0
    t[2] = (t[2] | termios.CLOCAL | termios.CREAD | termios.CS8) & ~termios.PARENB
    termios.tcsetattr(fd, termios.TCSANOW, t)
    print("live on", port, flush=True)
    out = open(log, "ab", buffering=0)
    tail, fire, session, state, last = b"", None, None, 0, 0.0
    try:
        while True:
            r, _, _ = select.select([fd], [], [], 0.2)
            data = b""
            if r:
                try: data = os.read(fd, 65536)
                except OSError: break
                if not data and not os.path.exists(port): break
            elif not os.path.exists(port): break
            if data:
                out.write(data)
                tail += data
                *lines, tail = tail.split(b"\n")
                for l in lines:
                    m = re.search(rb"SXNU1R ([0-9a-fA-F]{16}) ([0-9a-fA-F]{8}) (\w+) (\w+)(.*)", l)
                    if m:
                        print(l.decode("latin1").strip(), flush=True)
                        if m[3] == b"HELLO" and m[4] == b"OK": session = int(m[1], 16)
                        if m[3] == b"REBOOT" and m[4] == b"OK": state = 3
                    if fire is None and any(u.search(l) for u in until):
                        print("matched:", l.decode("latin1").strip()[:160], flush=True)
                        fire = time.time() + grace
            if fire is None and os.path.exists(log + ".reboot"):
                fire = time.time()
            now = time.time()
            if fire is not None and now >= fire and state < 3 and now - last > 1.0:
                last = now
                msg = frame(session, 1, "REBOOT") if session is not None else frame(0, 0, "HELLO")
                state = 2 if session is not None else 1
                os.write(fd, msg)
    finally:
        print("port gone", flush=True)

main()
