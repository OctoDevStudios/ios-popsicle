#!/usr/bin/python3 -I
"""Second pass over the prepared Ath12kWifi tree: what cnss2 (Android, this phone) tells the firmware, field by field."""
import os, re, sys
root = os.path.expanduser('~/17pm-work/src/Ath12kWifi/out/ath12k-src/')
def real(p):
    # a link into deps/linux: this tree gets its own copy, the reference stays as it is
    if os.path.islink(root + p):
        d = open(root + p).read(); os.remove(root + p); open(root + p, 'w').write(d)
for f in ('qmi.c', 'qmi.h', 'mhi.c', 'wifi7/hw.c'):
    real(f)
def rep(p, a, b):
    s = open(root + p).read()
    assert s.count(a) == 1, (p, a)
    open(root + p, 'w').write(s.replace(a, b))
# the chip's profile: a Qualcomm platform, no "internal sleep clock" (no qcom,sleep-clk-support in its device tree node)
p = 'wifi7/hw.c'; s = open(root + p).read()
k = s.index('qcc2072 hw1.0')
def after(s, a, b):
    e = s.index(a, k); return s[:e] + b + s[e + len(a):]
s = after(s, '.internal_sleep_clock = true,', '.internal_sleep_clock = false,')
s = after(s, '.download_aux_ucode = false,', '.download_aux_ucode = true,')
m = re.compile(r'\.qmi_cnss_feature_bitmap = BIT\(CNSS_QDSS_CFG_MISS_V01\) \|\s+BIT\(CNSS_PCIE_PERST_NO_PULL_V01\),').search(s, k)
s = s[:m.start()] + '.qmi_cnss_feature_bitmap = BIT(CNSS_QDSS_CFG_MISS_V01) | BIT(CNSS_AUX_UC_SUPPORT_V01),' + s[m.end():]
open(root + p, 'w').write(s)
rep('qmi.h', '#define QMI_WLANFW_HOST_CAP_REQ_MSG_V01_MAX_LEN		261', '#define QMI_WLANFW_HOST_CAP_REQ_MSG_V01_MAX_LEN		1017')
# cnss_wlfw_host_cap_send_sync
rep('qmi.c', '''	req.mem_cfg_mode = ab->qmi.target_mem_mode;
	req.mem_cfg_mode_valid = 1;
	req.bdf_support_valid = 1;''', '''	req.wake_msi_valid = 1;
	req.wake_msi = 13;
	req.bdf_support_valid = 1;''')
rep('qmi.c', '''	ret = ath12k_host_cap_parse_mlo(ab, &req);
	if (ret < 0)
		goto out;

	ret = qmi_txn_init(&ab->qmi.handle, &txn,
			   qmi_wlanfw_host_cap_resp_msg_v01_ei, &resp);''', '''	{
		u32 msi_lo = 0, msi_hi = 0;

		ath12k_hif_get_msi_address(ab, &msi_lo, &msi_hi);
		req.ddr_range_valid = 1;
		req.ddr_range[0].start = 0x18000000;
		req.ddr_range[0].size = 0x98010000;
		req.ddr_range[1].start = ((u64)msi_hi << 32) | (msi_lo & 0xfffff000);
		req.ddr_range[1].size = 0x1000;
	}
	req.host_build_type_valid = 1;
	req.host_build_type = QMI_WLANFW_HOST_BUILD_TYPE_SECONDARY_V01;
	req.platform_name_valid = 1;
	strncpy(req.platform_name, "Qualcomm Technologies, Inc. Popsicle based on SM8850", QMI_WLANFW_MAX_PLATFORM_NAME_LEN_V01);
	/* cnss_wlfw_host_cap_parse_mlo, PEACH */
	req.mlo_capable_valid = 1;
	req.mlo_capable = 1;
	req.mlo_chip_id_valid = 1;
	req.mlo_chip_id = 0;
	req.mlo_group_id_valid = 1;
	req.mlo_group_id = 0;
	req.max_mlo_peer_valid = 1;
	req.max_mlo_peer = 32;
	req.mlo_num_chips_valid = 1;
	req.mlo_num_chips = 1;
	req.mlo_chip_info_valid = 1;
	req.mlo_chip_info[0].chip_id = 0;
	req.mlo_chip_info[0].num_local_links = 2;
	req.mlo_chip_info[0].hw_link_id[0] = 0;
	req.mlo_chip_info[0].hw_link_id[1] = 1;
	req.mlo_chip_info[0].valid_mlo_link_id[0] = 1;
	req.mlo_chip_info[0].valid_mlo_link_id[1] = 1;

	ret = qmi_txn_init(&ab->qmi.handle, &txn,
			   qmi_wlanfw_host_cap_resp_msg_v01_ei, &resp);''')
rep('qmi.c', '#include "core.h"\n', '#include "core.h"\n#include "hif.h"\n')
rep('qmi.c', 'static int ath12k_host_cap_parse_mlo(struct ath12k_base *ab,', 'static int __maybe_unused ath12k_host_cap_parse_mlo(struct ath12k_base *ab,')
rep('mhi.c', '''		   ath12k_mhi_op_callback_to_str(cb));
''', '''		   ath12k_mhi_op_callback_to_str(cb));
	if (cb == MHI_CB_SYS_ERROR || cb == MHI_CB_FATAL_ERROR || cb == MHI_CB_EE_RDDM) {
		extern void nw_mhi_crash_report_on(struct mhi_controller *c, const char *why);
		nw_mhi_crash_report_on(mhi_cntrl, ath12k_mhi_op_callback_to_str(cb));
	}
''')
rep('qmi.c', 'static const struct qmi_elem_info qmi_wlanfw_host_cap_req_msg_v01_ei[]', '/* the firmware refuses the message (error 1, t31) without this descriptor: upstream never sent these ranges */\nstatic const struct qmi_elem_info qmi_wlanfw_host_ddr_range_ei[] = {\n\t{\n\t\t.data_type\t= QMI_UNSIGNED_8_BYTE,\n\t\t.elem_len\t= 1,\n\t\t.elem_size\t= sizeof(u64),\n\t\t.array_type\t= NO_ARRAY,\n\t\t.tlv_type\t= 0,\n\t\t.offset\t\t= offsetof(struct qmi_wlanfw_host_ddr_range, start),\n\t},\n\t{\n\t\t.data_type\t= QMI_UNSIGNED_8_BYTE,\n\t\t.elem_len\t= 1,\n\t\t.elem_size\t= sizeof(u64),\n\t\t.array_type\t= NO_ARRAY,\n\t\t.tlv_type\t= 0,\n\t\t.offset\t\t= offsetof(struct qmi_wlanfw_host_ddr_range, size),\n\t},\n\t{\n\t\t.data_type\t= QMI_EOTI,\n\t\t.array_type\t= NO_ARRAY,\n\t\t.tlv_type\t= QMI_COMMON_TLV_TYPE,\n\t},\n};\n\nstatic const struct qmi_elem_info qmi_wlanfw_host_cap_req_msg_v01_ei[]')
rep('qmi.c', '\t\t.offset\t\t= offsetof(struct qmi_wlanfw_host_cap_req_msg_v01,\n\t\t\t\t\t   ddr_range),\n', '\t\t.offset\t\t= offsetof(struct qmi_wlanfw_host_cap_req_msg_v01,\n\t\t\t\t\t   ddr_range),\n\t\t.ei_array\t= qmi_wlanfw_host_ddr_range_ei,\n')
print('peach2 applied')

# Android's order: m3, aux, then the QDSS trace config (the firmware starts after it): cnss_wlfw_qdss_dnld_send_sync
cfg = open(os.path.expanduser('~/17pm-work/device/live-t10/peach/qdss_trace_config_v2.cfg'), 'rb').read()
open(root + 'nw_qdss_v2.h', 'w').write('static const u8 nw_qdss_v2[] = {' + ','.join(str(b) for b in cfg) + '};\n')
s = open(root + 'wifi7/hw.c').read()
a = '.qmi_cnss_feature_bitmap = BIT(CNSS_QDSS_CFG_MISS_V01) | BIT(CNSS_AUX_UC_SUPPORT_V01),'
assert s.count(a) == 1
open(root + 'wifi7/hw.c', 'w').write(s.replace(a, '.qmi_cnss_feature_bitmap = BIT(CNSS_AUX_UC_SUPPORT_V01),'))
QD = r'''#include "nw_qdss_v2.h"
#define NW_QDSS_DATA 6144
struct nw_qdss_req {
	u8 total_size_valid;
	u32 total_size;
	u8 seg_id_valid;
	u32 seg_id;
	u8 data_valid;
	u32 data_len;
	u8 data[NW_QDSS_DATA];
	u8 end_valid;
	u8 end;
};
#define NW_F(t, l, sz, tlv, f) { .data_type = t, .elem_len = l, .elem_size = sz, .array_type = NO_ARRAY, .tlv_type = tlv, .offset = offsetof(struct nw_qdss_req, f) }
static const struct qmi_elem_info nw_qdss_req_ei[] = {
	NW_F(QMI_OPT_FLAG, 1, sizeof(u8), 0x10, total_size_valid),
	NW_F(QMI_UNSIGNED_4_BYTE, 1, sizeof(u32), 0x10, total_size),
	NW_F(QMI_OPT_FLAG, 1, sizeof(u8), 0x11, seg_id_valid),
	NW_F(QMI_UNSIGNED_4_BYTE, 1, sizeof(u32), 0x11, seg_id),
	NW_F(QMI_OPT_FLAG, 1, sizeof(u8), 0x12, data_valid),
	NW_F(QMI_DATA_LEN, 1, sizeof(u16), 0x12, data_len),
	{ .data_type = QMI_UNSIGNED_1_BYTE, .elem_len = NW_QDSS_DATA, .elem_size = sizeof(u8), .array_type = VAR_LEN_ARRAY, .tlv_type = 0x12, .offset = offsetof(struct nw_qdss_req, data) },
	NW_F(QMI_OPT_FLAG, 1, sizeof(u8), 0x13, end_valid),
	NW_F(QMI_UNSIGNED_1_BYTE, 1, sizeof(u8), 0x13, end),
	{ .data_type = QMI_EOTI, .array_type = NO_ARRAY, .tlv_type = QMI_COMMON_TLV_TYPE },
};
static int nw_qdss_send(struct ath12k_base *ab)
{
	struct nw_qdss_req *req = kzalloc(sizeof(*req), GFP_KERNEL);
	const u8 *p = nw_qdss_v2;
	u32 left = sizeof(nw_qdss_v2);
	int ret = 0;

	if (!req)
		return -ENOMEM;
	while (left && !ret) {
		struct qmi_wlanfw_aux_uc_info_resp_msg_v01 resp = {};
		struct qmi_txn txn;

		req->total_size_valid = 1;
		req->total_size = left;
		req->seg_id_valid = 1;
		req->data_valid = 1;
		req->end_valid = 1;
		req->data_len = left > NW_QDSS_DATA ? NW_QDSS_DATA : left;
		req->end = left <= NW_QDSS_DATA;
		memcpy(req->data, p, req->data_len);
		ret = qmi_txn_init(&ab->qmi.handle, &txn, qmi_wlanfw_aux_uc_info_resp_msg_v01_ei, &resp);
		if (ret < 0)
			break;
		ret = qmi_send_request(&ab->qmi.handle, NULL, &txn, 0x0044, 6167, nw_qdss_req_ei, req);
		if (ret < 0) {
			qmi_txn_cancel(&txn);
			break;
		}
		ret = qmi_txn_wait(&txn, msecs_to_jiffies(ATH12K_QMI_WLANFW_TIMEOUT_MS));
		if (ret < 0)
			break;
		if (resp.resp.result != QMI_RESULT_SUCCESS_V01) {
			ath12k_warn(ab, "QDSS config refused: result %d err %d\n", resp.resp.result, resp.resp.error);
			ret = -EINVAL;
			break;
		}
		ret = 0;
		left -= req->data_len;
		p += req->data_len;
		req->seg_id++;
	}
	ath12k_warn(ab, "QDSS config sent: %d, %u bytes left\n", ret, left);
	kfree(req);
	return ret;
}

'''
s = open(root + 'qmi.c').read()
a = 'static void ath12k_qmi_msg_mem_request_cb(struct qmi_handle *qmi_hdl,'
assert s.count(a) == 1
k = s.index('int ath12k_qmi_wlanfw_m3_info_send(struct ath12k_base *ab)')
b = 'ath12k_warn(ab, "qmi failed to send aux_uc info req: %d\\n", ret);\n\t\t\treturn ret;\n\t\t}\n\t}\n'
assert s.count(b) == 1
s = s.replace(b, b + '\n\tret = nw_qdss_send(ab);\n\tif (ret < 0)\n\t\treturn ret;\n')
# before the function that calls it, after the aux response descriptor
m = 'int ath12k_qmi_wlanfw_m3_info_send(struct ath12k_base *ab)'
s = s.replace(m, QD + m, 1)
open(root + 'qmi.c', 'w').write(s)
print('qdss applied')

# traces: what the firmware answers once the radio is on
for f in ('wmi.c', 'core.c'):
    real(f)
rep('core.c', 'unsigned int ath12k_debug_mask;', 'unsigned int ath12k_debug_mask = ATH12K_DBG_WMI | ATH12K_DBG_MAC;')
rep('wmi.c', '''	id = le32_get_bits(cmd_hdr->cmd_id, WMI_CMD_HDR_CMD_ID);

	if (!skb_pull(skb, sizeof(struct wmi_cmd_hdr)))
		goto out;

	switch (id) {
		/* Process all the WMI events here */''', '''	id = le32_get_bits(cmd_hdr->cmd_id, WMI_CMD_HDR_CMD_ID);
	ath12k_dbg(ab, ATH12K_DBG_WMI, "NW wmi event 0x%x, %u bytes\\n", id, skb->len);

	if (!skb_pull(skb, sizeof(struct wmi_cmd_hdr)))
		goto out;

	switch (id) {
		/* Process all the WMI events here */''')
print('traces applied')

# 5 novembre, essai fait puis annule : WMI_SEND_TIMEOUT_HZ passe de 3 s a 20 s (rep() ci-dessous),
# pour savoir si le firmware est lent. Resultat (c6, c7) : toujours aucun credit apres 20 s, donc
# la puce ne repond plus du tout. La valeur est revenue a 3 s ; le patch est laisse en commentaire.
# real('wmi.h')
# rep('wmi.h', '#define WMI_SEND_TIMEOUT_HZ (3 * HZ)', '#define WMI_SEND_TIMEOUT_HZ (20 * HZ)')
# print('wmi send timeout 20 s')

# 5 novembre : sonde de vie du firmware (nw_wifi_qmi_probe dans src/nw_wifi.c) : la demande de
# capacites doit etre appelable depuis un autre fichier du module.
rep('qmi.c', 'static noinline_for_stack\nint ath12k_qmi_request_target_cap(struct ath12k_base *ab)',
    'noinline_for_stack\nint ath12k_qmi_request_target_cap(struct ath12k_base *ab)')
print('qmi probe exported')

# 5 novembre : Android n'active pas le journal du firmware (pas de gEnablefwlog dans
# WCNSS_qcom_cfg.ini). Le firmware envoie alors des rafales de WMI_DIAG_EVENTID (0x1d011,
# ~1480 octets, jusqu'a 26 d'un coup) juste avant de se bloquer (c16). On fait comme Android.
# Essai fait puis annule (c18-c20 : 0 reussite sur 3). Android n'active pas le journal du
# firmware, mais le desactiver ne nous aide pas ; on revient a enable_fwlog = 1.
# rep('qmi.c', 'req.enable_fwlog = 1;', 'req.enable_fwlog = 0;')
# print('fwlog disabled')
