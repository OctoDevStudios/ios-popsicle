#!/usr/bin/python3 -I
"""Recompile files of the PANDORA kernel on this Mac, with the commands of a CI build.

  mac/kernel_cc.py WORK OUTDIR [--all] [-j N] SOURCE...

WORK: holds ci.log, bt/ (xnu-buildtree) and obj/ (xnu-objects). SOURCE: path under xnu/, e.g. bsd/dev/pandora_wlan.c.
Sources are taken from bt/xnu. Objects go to OUTDIR/<config-relative path>; mac/relink_kernel.py --overlay OUTDIR links them.
"""
import concurrent.futures as cf, os, re, shlex, subprocess, sys, time
XC15 = '/Applications/Xcode_15.0.1.app/Contents/Developer'
if os.path.isdir(XC15): os.environ.setdefault('DEVELOPER_DIR', XC15)   # the compiler of the CI build: same code as CI
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
# What xnu's Makefile.template does after compiling (SEG_HACK): libsa goes to __KLD and __KLDDATA, listed files to __HIB.
SEG = os.path.join(BT, 'build/xnu.obj/SETUP/setsegname/setsegname')
def seg(obj, *a):
    subprocess.run([SEG, *a, '-o', obj + '__', obj], check=True, capture_output=True); os.replace(obj + '__', obj)
def segments(src, obj):
    comp = component(src)
    if comp == 'libsa':
        seg(obj, '-s', '__TEXT', '-n', '__KLD'); seg(obj, '-i', '__KLD', '-n', '__KLDDATA'); return
    ci = os.path.join(work, 'obj/DEVELOPMENT_ARM64_PANDORA', comp, 'DEVELOPMENT', os.path.basename(obj))
    if os.path.exists(ci):
        o = subprocess.run(['xcrun', 'otool', '-l', ci], capture_output=True, text=True).stdout
        if re.search(r'segname __HIB\b', o): seg(obj, '-n', '__HIB')
def build(src):
    args = cmds[src]; new = [CLANG if os.path.basename(args[0]) == 'clang' else CLANG + '++', '-w', '-ferror-limit=20']
    obj_dir = os.path.join(out, component(src), 'DEVELOPMENT'); os.makedirs(obj_dir, exist_ok=True)
    ext = 'cpo' if args[0].endswith('++') else 'o'
    obj = os.path.join(obj_dir, os.path.basename(src).rsplit('.', 1)[0] + '.' + ext)
    for x in args[1:]:
        if x.startswith('-W') or x.startswith('-ferror-limit') or x.startswith('--serialize'): continue
        x = re.sub(r'/Applications/Xcode_[^/]*/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX[0-9.]*\.sdk/*', SDK + '/', x)
        new.append(x.replace(DXB, BT))
    new[-1:-1] = ['-o', obj, '-fmacro-prefix-map=' + BT + '=' + DXB, '-fdebug-prefix-map=' + BT + '=' + DXB]   # same __FILE__ strings as CI
    cwd = os.path.join(BT, CFG, component(src), 'DEVELOPMENT')
    try:
        r = subprocess.run(new, cwd=cwd, capture_output=True, text=True)
    except OSError as e:
        return src, 1, repr(e)
    if r.returncode == 0: segments(src, obj)
    return src, r.returncode, r.stderr[-1500:]
want = sorted(cmds) if every else a
t = time.time(); bad = []
with cf.ThreadPoolExecutor(jobs) as p:
    for src, rc, err in p.map(build, want):
        if rc: bad.append(src); print('FAIL', src, '\n', err)
print(f'{len(want)} files, {len(bad)} failed, {time.time() - t:.0f} s')
sys.exit(1 if bad else 0)
