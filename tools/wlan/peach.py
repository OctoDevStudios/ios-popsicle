#!/usr/bin/python3 -I
"""Adapt a prepared Ath12kWifi tree to the WCN7880 "peach" (17cb:110e) of the Xiaomi 17 Pro Max.
Usage: peach.py ATH12KWIFI. Every change mirrors Android's cnss2/MHI behaviour seen on this phone (tests t16-t21)."""
import sys
from pathlib import Path
root = Path(sys.argv[1])
def copy(p):
    if p.is_symlink():
        t = p.read_text(); p.unlink(); p.write_text(t)
def rep(p, a, b, n=1):
    copy(p); s = p.read_text()
    assert s.count(a) >= 1, (str(p), a)
    if a in s and b in s and b.startswith(a): return
    p.write_text(s.replace(a, b) if n == 0 else s.replace(a, b, n))
A = root / 'out/ath12k-src'
# The chip: closest upstream relative is the QCC2072 (remap window 0x3278, aux ucode, m3 by the driver).
pci = A / 'wifi7/pci.c'
rep(pci, '#define QCC2072_DEVICE_ID		0x1112\n', '#define QCC2072_DEVICE_ID		0x1112\n#define PEACH_DEVICE_ID			0x110e\n')
rep(pci, '	{ PCI_VDEVICE(QCOM, QCC2072_DEVICE_ID) },\n', '	{ PCI_VDEVICE(QCOM, QCC2072_DEVICE_ID) },\n	{ PCI_VDEVICE(QCOM, PEACH_DEVICE_ID) },\n')
rep(pci, '	case QCC2072_DEVICE_ID:\n		ab->id.bdf_search', '	case PEACH_DEVICE_ID:\n	case QCC2072_DEVICE_ID:\n		ab->id.bdf_search')
# MHI: what Android's controller gives the chip; without it SYS_ERR at M0 (t17-t20).
M = root / 'src/nw_mhi.c'
rep(M, '''static const struct mhi_channel_config nw_channels[] = {
''', '''static const struct mhi_channel_config nw_channels[] = {
  { .num = 0, .name = "LOOPBACK", .num_elements = 32, .event_ring = 1, .dir = DMA_TO_DEVICE, .ee_mask = 0x4, .doorbell = MHI_DB_BRST_DISABLE },
  { .num = 1, .name = "LOOPBACK", .num_elements = 32, .event_ring = 1, .dir = DMA_FROM_DEVICE, .ee_mask = 0x4, .doorbell = MHI_DB_BRST_DISABLE },
  { .num = 4, .name = "DIAG", .num_elements = 64, .event_ring = 1, .dir = DMA_TO_DEVICE, .ee_mask = 0x4, .doorbell = MHI_DB_BRST_DISABLE },
  { .num = 5, .name = "DIAG", .num_elements = 64, .event_ring = 1, .dir = DMA_FROM_DEVICE, .ee_mask = 0x4, .doorbell = MHI_DB_BRST_DISABLE },
''')
rep(M, '''  { .num_elements = 256, .irq_moderation_ms = 1, .irq = 2, .mode = MHI_DB_BRST_DISABLE, .priority = 1 },
''', '''  { .num_elements = 256, .irq_moderation_ms = 0, .irq = 2, .mode = MHI_DB_BRST_DISABLE, .priority = 1 },
  { .num_elements = 32, .irq_moderation_ms = 0, .irq = 1, .mode = MHI_DB_BRST_DISABLE, .priority = 2 },
  { .num_elements = 256, .irq_moderation_ms = 0, .irq = 2, .mode = MHI_DB_BRST_DISABLE, .priority = 1, .client_managed = true, .offload_channel = true },
''')
rep(M, '.max_channels = 128, .timeout_ms = 2000', '.max_channels = 72, .timeout_ms = 10000')
rep(M, '  c->iova_start = 0; c->iova_stop = dma_limit;\n', '  c->iova_start = 0x18000000; c->iova_stop = 0xb0000000;  /* cnss_pci_init_smmu */\n  c->rddm_size = 0x780000;\n')
rep(M, 'int mhi_init_mmio(struct mhi_controller *mhi_cntrl);\n', '''int mhi_init_mmio(struct mhi_controller *mhi_cntrl);
/* mhi_misc_init_mmio of Android's tree: bandwidth scaling on ring 2 and host notification are advertised. */
void nw_mhi_caps(struct mhi_controller *c) {
  u32 off = readl(c->regs + 0x24);
  for (int n = 0; off && off < 0x1000 && n < 16; n++) {
    u32 cap = readl(c->regs + off);
    if ((cap >> 24) == 3) writel((126u << 25) | (1u << 24) | (2u << 19), c->regs + off + 4);
    else if ((cap >> 24) == 6) writel((1u << 31) | 124u, c->regs + off + 4);
    off = (cap >> 12) & 0xfff;
  }
}
''')
rep(M, '  static int done; if (done) return; done = 1;\n  lx_delay_ms(NW_BOOT_SETTLE_MS);\n  int r = mhi_init_mmio(c);\n', '  /* Android goes straight to the image (mhi log); its contexts are written after READY. */\n  (void)c; return;\n  int r = 0;\n')
I = root / 'out/os-src/mhi-init.c'   # the patched copy the module uses (linux-completion-workqueues.patch)
copy(I); s = I.read_text()
k = s.index('int mhi_init_mmio(struct mhi_controller *mhi_cntrl)')
e = s.index('\treturn 0;\n}', k)
I.write_text(s[:e] + '\t{ extern void nw_mhi_caps(struct mhi_controller *); nw_mhi_caps(mhi_cntrl); }\n' + s[e:])
# BHIe: Linux 7's boot.c already skips the first 512 KiB when a second ELF header follows.
# Firmware WLAN.GNG refuses AUX_UC info (QMI error 90, t27): no aux ucode for this chip through QMI here.
H = A / 'wifi7/hw.c'
copy(H); s = H.read_text()
k = s.index('.name = "qcc2072 hw1.0"')
e = s.index('.download_aux_ucode = true,', k)
s = s[:e] + '.download_aux_ucode = false,' + s[e+len('.download_aux_ucode = true,'):]
b = s.index('BIT(CNSS_AUX_UC_SUPPORT_V01)', k)
pre = s.rfind('|', k, b)
s = s[:pre].rstrip() + s[b+len('BIT(CNSS_AUX_UC_SUPPORT_V01)'):]
H.write_text(s)
print('peach adaptation applied')
