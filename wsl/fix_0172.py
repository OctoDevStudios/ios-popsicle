W = '/mnt/d/work/ios_pandora/wsl/'
# Adreno 840 bring-up, level 10: the CP (hw_init's required part, SQE start, CP_ME_INIT)
# (bsd/dev/pandora_gpu.c, boot-arg pandora_gpu=10).
open('bsd/dev/pandora_gpu.c', 'w').write(open(W + 'pandora_gpu.c').read().replace('\r', ''))
print('patched')
