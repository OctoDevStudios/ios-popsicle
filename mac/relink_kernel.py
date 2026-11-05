#!/usr/bin/python3 -I
"""Relink a PANDORA kernel on this Mac from a CI run's objects, with another Wi-Fi driver object (no C compile).

  mac/relink_kernel.py WORK NW_ALL_O OUT [--overlay DIR]

DIR: objects from mac/kernel_cc.py, used in place of the CI objects of the same name.

WORK: xnu-objects artifact unpacked (obj/, linklibs/) and ci.log (`gh run view ID --log`).
Writes OUT/kernel.development.pandora (stripped) and OUT/kernel.development.pandora.unstripped.
"""
import os, re, shlex, subprocess, sys
XC15 = '/Applications/Xcode_15.0.1.app/Contents/Developer'
if os.path.isdir(XC15): os.environ.setdefault('DEVELOPER_DIR', XC15)   # the linker of the CI build
work, nw, out = (os.path.abspath(os.path.expanduser(a)) for a in sys.argv[1:4])
overlay = None
if '--overlay' in sys.argv:
    overlay = os.path.abspath(os.path.expanduser(sys.argv[sys.argv.index('--overlay') + 1]))
os.makedirs(out, exist_ok=True)
cfg = os.path.join(work, 'obj/DEVELOPMENT_ARM64_PANDORA')
line = next(l for l in open(os.path.join(work, 'ci.log'), errors='replace')
            if 'clang++ ' in l and 'kernel.development.pandora.unstripped' in l and '-filelist' in l)
cmd = line[line.index('/Applications/Xcode'):].strip()
cmd = re.sub(r'\x1b\[[0-9;]*m', '', cmd)
args = shlex.split(cmd)
RUN = '/Users/runner/work/popsicle-ios/popsicle-ios/dxb/build/xnu.obj/DEVELOPMENT_ARM64_PANDORA'
sdk = subprocess.run(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], capture_output=True, text=True).stdout.strip()
libs = os.path.join(work, 'linklibs')
cc = os.path.join(libs, 'libcc_kext.a')
if not os.path.exists(cc):
    os.symlink('libclang_rt.cc_kext.a', cc)
fl = os.path.join(out, 'link.filelist')
used = total = 0
with open(fl, 'w') as f:
    for p in open(os.path.join(cfg, 'link.filelist')):
        q = p.strip().replace(RUN, cfg)
        if overlay:
            rel = os.path.relpath(q, cfg); comp = rel.split('/')[0]; stem = os.path.basename(q).rsplit('.', 1)[0]
            for ext in ('o', 'cpo'):
                o = os.path.join(overlay, comp, 'DEVELOPMENT', stem + '.' + ext)
                if os.path.exists(o):
                    q = o; used += 1; break
        total += 1
        f.write(q + '\n')
if overlay: print(f'overlay: {used} of {total} objects replaced')
new = ['xcrun', 'clang++']
i = 1
while i < len(args):
    a = args[i]
    if a == '-filelist':
        new += ['-filelist', fl]; i += 2; continue
    if a == '-o':
        new += ['-o', os.path.join(out, 'kernel.development.pandora.unstripped')]; i += 2; continue
    if a == '-isysroot':
        new += ['-isysroot', sdk]; i += 2; continue
    if a.endswith('/bsd/dev/nw_all.o'):
        new.append(nw); i += 1; continue
    if a.startswith('-L') and 'fakeroot' in a:
        new.append('-L' + libs); i += 1; continue
    new.append(a.replace(RUN, cfg))
    i += 1
new += ['-L' + libs]
print(' '.join(new)[:300], '...')
r = subprocess.run(new, cwd=cfg, capture_output=True, text=True)
print(r.stderr[-3000:])
if r.returncode:
    sys.exit('link failed')
u = os.path.join(out, 'kernel.development.pandora.unstripped')
k = os.path.join(out, 'kernel.development.pandora')
subprocess.run(['xcrun', 'strip', '-S', '-o', k, u], check=True)
print(os.path.getsize(k), 'bytes')
