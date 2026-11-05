#!/usr/bin/python3 -I
"""Recompile files of the PANDORA kernel on this Mac, with the commands of a CI build.

  mac/kernel_cc.py WORK OUTDIR [--all] [-j N] SOURCE...

WORK: holds ci.log, bt/ (xnu-buildtree) and obj/ (xnu-objects). SOURCE: path under xnu/, e.g. bsd/dev/pandora_wlan.c.
Sources are taken from bt/xnu. Objects go to OUTDIR/<config-relative path>; mac/relink_kernel.py --overlay OUTDIR links them.
"""
import concurrent.futures as cf, os, re, shlex, subprocess, sys, time
a = sys.argv[1:]
work, out = os.path.abspath(os.path.expanduser(a[0])), os.path.abspath(os.path.expanduser(a[1]))
a = a[2:]; every = '--all' in a; jobs = 6
if every: a.remove('--all')
if '-j' in a: k = a.index('-j'); jobs = int(a[k + 1]); del a[k:k + 2]
DXB = '/Users/runner/work/popsicle-ios/popsicle-ios/dxb'
BT = os.path.join(work, 'bt'); CFG = 'build/xnu.obj/DEVELOPMENT_ARM64_PANDORA'
SDK = subprocess.run(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], capture_output=True, text=True).stdout.strip()
CLANG = subprocess.run(['xcrun', '--find', 'clang'], capture_output=True, text=True).stdout.strip()
ansi = re.compile(r'\x1b\[[0-9;]*m')
cmds = {}
for line in open(os.path.join(work, 'ci.log'), errors='replace'):
    if ' -c ' not in line or 'clang' not in line or DXB not in line: continue
    line = ansi.sub('', line); i = line.find('/Applications/Xcode')
    if i < 0: continue
    try: args = shlex.split(line[i:].strip())
    except ValueError: continue
    if os.path.basename(args[0]) not in ('clang', 'clang++') or '-c' not in args: continue
    src = args[-1]
    if src.startswith(DXB + '/xnu/'): cmds[src[len(DXB) + 5:]] = args
    elif src.startswith(DXB + '/' + CFG + '/'): cmds[src[len(DXB) + 1:]] = args   # generated: mig, iig
def component(src):
    if src.startswith(CFG + '/'): return src.split('/')[3]
    return src.split('/')[0]
def build(src):
    args = cmds[src]; new = [CLANG if os.path.basename(args[0]) == 'clang' else CLANG + '++', '-w', '-ferror-limit=20']
    obj_dir = os.path.join(out, component(src), 'DEVELOPMENT'); os.makedirs(obj_dir, exist_ok=True)
    ext = 'cpo' if args[0].endswith('++') else 'o'
    obj = os.path.join(obj_dir, os.path.basename(src).rsplit('.', 1)[0] + '.' + ext)
    for x in args[1:]:
        if x.startswith('-W') or x.startswith('-ferror-limit') or x.startswith('--serialize'): continue
        x = re.sub(r'/Applications/Xcode_[^/]*/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX[0-9.]*\.sdk/*', SDK + '/', x)
        new.append(x.replace(DXB, BT))
    new[-1:-1] = ['-o', obj]
    cwd = os.path.join(BT, CFG, component(src), 'DEVELOPMENT')
    try:
        r = subprocess.run(new, cwd=cwd, capture_output=True, text=True)
    except OSError as e:
        return src, 1, repr(e)
    return src, r.returncode, r.stderr[-1500:]
want = sorted(cmds) if every else a
t = time.time(); bad = []
with cf.ThreadPoolExecutor(jobs) as p:
    for src, rc, err in p.map(build, want):
        if rc: bad.append(src); print('FAIL', src, '\n', err)
print(f'{len(want)} files, {len(bad)} failed, {time.time() - t:.0f} s')
sys.exit(1 if bad else 0)
