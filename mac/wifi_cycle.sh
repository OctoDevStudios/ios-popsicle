#!/bin/bash
# Pilote Wi-Fi modifié -> objet -> noyau réassemblé -> test en RAM -> résumé du journal.
#   wifi_cycle.sh tNN [SECONDES] ["motif d'arrêt 1" "motif 2" ...]
# Ne touche à aucune partition : la seule voie de démarrage est mac/boot_ios.sh (fastboot boot).
set -u
NAME=${1:?nom du test, ex. t44}; SECS=${2:-72}; shift; shift 2>/dev/null
L=~/17pm-work/src/popsicle-ios/mac/logs
[ -e "$L/$NAME.txt" ] || [ -e "$L/$NAME.live" ] && { echo "REFUS: $NAME existe déjà, prends un autre nom"; exit 9; }
export PATH=$HOME/17pm-work/bin:$PATH
bash ~/17pm-work/wl/rebuild.sh 2>&1 | tail -2 | cut -c1-200
cd ~/17pm-work/kernel/relink && /usr/bin/python3 -I ~/17pm-work/src/popsicle-ios/mac/relink_kernel.py . ~/17pm-work/src/popsicle-ios/xnu/vendor/nw_all.o "$NAME" 2>&1 | tail -1 || exit 1
[ -f "$NAME/kernel.development.pandora" ] || { echo "ÉCHEC: pas de noyau"; exit 1; }
U=$'CRASH: end\nNW direct scan done\nstuck: wmi credits'
for m in "$@"; do U+=$'\n'"$m"; done
SIMARG="" UNTIL="$U" GRACE=${GRACE:-3} SECS=$SECS bash ~/17pm-work/tools/test_kernel.sh ~/17pm-work/kernel/relink/$NAME/kernel.development.pandora "$NAME" local >/dev/null 2>&1
rc=$?; echo "test terminé, code $rc (3 = le script n'a pas revu Android : vérifier adb, ce n'est pas forcément grave)"
bash ~/17pm-work/tools/log_summary.sh "$NAME"
