#!/bin/bash
# Résumé d'un test Wi-Fi : lit tNN.txt, sinon tNN.live. Lecture seule.
NAME=${1:?nom du test}; cd ~/17pm-work/src/popsicle-ios/mac/logs || exit 1
F=$NAME.txt; [ -f "$F" ] || F=$NAME.live; [ -f "$F" ] || { echo "aucun journal pour $NAME"; exit 1; }
echo "== fichier: $F, $(wc -l < "$F") lignes, modifié $(stat -f '%Sm' "$F"); dernière ligne:"; tail -1 "$F" | cut -c1-120
echo "== erreurs système: $(grep -a -c 'System error' "$F")"
echo "== étapes"; grep -a -o 'QDSS config sent.*\|radio on applied\|radio request failed: [-0-9]*\|scan asked.*\|NW direct scan -> [-0-9]*\|NW direct scan done.*\|scan done: [0-9]* networks\|stuck: wmi credits.*\|restart ordered by the Mac' "$F" | cut -c1-100 | uniq -c | head -30
echo "== réseaux"; grep -a -o 'NW network.*' "$F" | cut -c1-90 | head -40
echo "== événements WMI (groupe scan: 0x3xxx)"; grep -a -o 'NW wmi event 0x[0-9a-f]*' "$F" | sort | uniq -c | sort -rn | head -14
echo "== rapport de crash"; grep -a 'CRASH: ' "$F" | grep -a -v 'CRASH: 2+' | head -12 | cut -c1-170
echo "== panique"; grep -a -i -n 'panic(cpu\|panic string\|unexpected SIGKILL of launchd' "$F" | head -4 | cut -c1-150
