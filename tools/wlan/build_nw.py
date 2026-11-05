#!/usr/bin/python3 -I
"""Compile the Ath12kWifi module for XNU arm64 into one relocatable object (out/nw_all.o). Host-side tool."""
import os, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
root = Path(os.path.expanduser('~/17pm-work/src/Ath12kWifi'))
out = Path(os.path.expanduser('~/17pm-work/wl/obj')); out.mkdir(parents=True, exist_ok=True)
CL = '/Library/Developer/CommandLineTools/usr/lib/clang/21.0.0/include'
base = ['/usr/bin/clang','-c','-target','arm64-apple-macos13.0','-mkernel','-fno-stack-protector','-nostdinc','-isystem',str(root/'shim/libc'),'-isystem',CL,
 '-std=gnu11','-O2','-w','-g0','-DCONFIG_ATH12K_DEBUG','-DCONFIG_CFG80211=1','-DCONFIG_MAC80211=1','-DCONFIG_MAC80211_STA_HASH_MAX_SIZE=0','-DCONFIG_MAC80211_RC_DEFAULT=""',
 '-fno-strict-aliasing','-fwrapv','-Wno-incompatible-pointer-types','-include','lx_pci.h']
for d in ('shim/include','include','src','out/pinned','out','out/ath12k-src'):
    base += ['-I',str(root/d)]
jobs=[]
for line in (root/'tools/sources.txt').read_text().splitlines():
    line=line.strip()
    if not line or line.startswith('#'): continue
    tree,_,name = line.partition(':') if ':' in line else ('','',line)
    extra=[]
    if tree=='mhi' and name=='init.c': src=root/'out/os-src/mhi-init.c'; extra+=['-I',str(root/'out/mhi-src')]
    elif tree in ('mac80211','cfg80211','crypto','ath12k','mhi'):
        src=root/'out'/({'ath12k':'ath12k-src','mhi':'mhi-src'}.get(tree,tree))/name
    elif tree=='generated': src=root/'out'/name
    elif tree=='qmi': src=root/'out/os-src'/name
    else: src=root/name
    if tree in('mac80211','cfg80211'): extra+=['-I',str(root/'out'/tree)]
    if tree=='crypto' or name=='src/nw_crypto_mac80211.c': extra+=['-I',str(root/'shim/crypto'),'-I',str(root/'out/crypto')]
    if name in('src/nw_fils.c','src/nw_crypto_mac80211.c'): extra+=['-I',str(root/'out/mac80211')]
    if name.startswith('src/nw_cfg80211_'): extra+=['-I',str(root/'out/cfg80211')]
    if tree=='mhi' or name in ('src/nw_mhi.c',): extra+=['-I',str(root/'out/mhi-src')]
    if tree=='crypto' and name=='aes-siv.c': extra+=['-Daes_siv_encrypt=nw_aes_siv_encrypt','-Daes_siv_decrypt=nw_aes_siv_decrypt']
    o=out/(((tree+'_') if tree else '')+name.replace('/','_').replace('.c','.o'))
    jobs.append((src,o,extra))
def cc(j):
    s,o,e=j
    if not s.exists(): return (s,'missing')
    r=subprocess.run(base[:2]+e+base[2:]+[str(s),'-o',str(o)],capture_output=True,text=True)
    return (s,r.stderr[-700:] if r.returncode else None)
with ThreadPoolExecutor(8) as p: res=list(p.map(cc,jobs))
bad=[r for r in res if r[1]]
print(len(jobs),'sources,',len(bad),'failed')
for s,e in bad[:40]: print('--',s.name,'|',[l for l in (e or '').splitlines() if 'error:' in l][:2])
if bad: sys.exit(1)
