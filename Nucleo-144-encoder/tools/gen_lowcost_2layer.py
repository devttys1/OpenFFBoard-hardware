"""Generate a 2-layer low-cost-fab rules file and stackup for the Nucleo-144 encoder board.

Rule records are cloned from real Altium records (the board's own Rules6 stream and
the JLCPCB 6-layer .RUL the user already imports elsewhere) so every field Altium
expects is present; only the values below are changed.

Writes LowCost-2layer-JLCPCB-PCBWay.RUL and LowCost-2layer-1.6mm.stackup next to the
PcbDoc. Import them in Altium with Design > Rules > Import Rules and
Layer Stack Manager > File > Load Stackup From File.

Needs olefile (pip install olefile). Close the PcbDoc in Altium first if it is
open over a network share, so the Rules6 stream read here is the saved one.

    python3 gen_lowcost_2layer.py [--ref-rul X.RUL] [--ref-stackup X.stackup]
"""
import argparse, os, olefile, struct, random, string, uuid, datetime, collections

_ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
_ap.add_argument('--pcbdoc', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'PCB1.PcbDoc'))
_ap.add_argument('--ref-rul', default=os.path.expanduser('~/git/rak-mppt-baseboard/JLCPCB-6layer.RUL'))
_ap.add_argument('--ref-stackup', default=os.path.expanduser('~/git/rak-mppt-baseboard/JLCPCB-6layer.stackup'))
_args = _ap.parse_args()

PCBDOC = os.path.normpath(_args.pcbdoc)
OUT = os.path.dirname(PCBDOC) + os.sep
REF_RUL = _args.ref_rul
REF_STACK = _args.ref_stackup


def mil(mm):
    return f'{mm / 0.0254:.4f}'.rstrip('0').rstrip('.') + 'mil'


def parse(s):
    s = s.strip().strip('\x00\xb6').strip('|')
    return collections.OrderedDict(kv.split('=', 1) for kv in s.split('|') if '=' in kv)


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


# ---- templates, keyed by RULEKIND (reference file wins over the board's defaults) ----
board = []
d = olefile.OleFileIO(PCBDOC).openstream('Rules6/Data').read()
i = 0
while i < len(d):
    n = struct.unpack('<I', d[i + 2:i + 6])[0]
    board.append(parse(d[i + 6:i + 6 + n].decode('latin1')))
    i += 6 + n
ref = [parse(l) for l in open(REF_RUL, 'rb').read().decode('latin1').split('\r\n') if 'RULEKIND=' in l]

tmpl = {}
for r in board + ref:
    tmpl.setdefault(r['RULEKIND'], r)
for r in ref:  # prefer the reference record whose scope is All
    if r['SCOPE1EXPRESSION'] == 'All':
        tmpl[r['RULEKIND']] = r

rules = []


def rule(kind, name, priority=1, scope1='All', scope2='All', **vals):
    r = collections.OrderedDict(tmpl[kind])
    r.update(NAME=name, PRIORITY=str(priority), SCOPE1EXPRESSION=scope1, SCOPE2EXPRESSION=scope2,
             ENABLED='TRUE', UNIQUEID=uid(), COMMENT=vals.pop('COMMENT', ' '))
    for k, v in vals.items():
        r[k] = v
    rules.append(r)


C = 'JLCPCB/PCBWay 2-layer standard tier'
# Electrical
rule('Clearance', 'Clearance-ViaToPad', 1, 'IsVia', 'IsPad', GAP=mil(0.2), GENERICCLEARANCE=mil(0.2),
     OBJECTCLEARANCES='', IGNOREPADTOPADCLEARANCEINFOOTPRINT='FALSE', NETSCOPE='DifferentNets',
     COMMENT='JLCPCB via-to-pad minimum 0.2 mm')
rule('Clearance', 'Clearance', 2, GAP=mil(0.15), GENERICCLEARANCE=mil(0.15), OBJECTCLEARANCES='',
     IGNOREPADTOPADCLEARANCEINFOOTPRINT='FALSE', NETSCOPE='DifferentNets',
     COMMENT=C + ': 0.15 mm, above the 0.10 mm fab minimum and equal to JLCPCB SMD pad-to-pad')
rule('ShortCircuit', 'ShortCircuit')
rule('UnRoutedNet', 'UnRoutedNet')
rule('UnpouredPolygon', 'UnpouredPolygon')
# Routing
rule('Width', 'Width', MINLIMIT=mil(0.15), PREFEREDWIDTH=mil(0.25), MAXLIMIT=mil(5.0), COMMENT=C)
rule('RoutingTopology', 'RoutingTopology')
rule('RoutingPriority', 'RoutingPriority')
rule('RoutingLayers', 'RoutingLayers')
rule('RoutingCorners', 'RoutingCorners')
rule('RoutingVias', 'RoutingVias', HOLEWIDTH=mil(0.3), WIDTH=mil(0.6), MINHOLEWIDTH=mil(0.3),
     MAXHOLEWIDTH=mil(1.0), MINWIDTH=mil(0.6), MAXWIDTH=mil(2.0),
     COMMENT='0.3 mm drill avoids the small-via surcharge; 0.15 mm ring meets PCBWay')
rule('FanoutControl', 'Fanout_Default')
dp = {k: {'MIN': mil(0.15), 'MAX': mil(0.5), 'PREF': mil(0.25)}[k.rsplit('_', 1)[1][:-5]]
      for k in tmpl['DiffPairsRouting'] if k.endswith(('_MINWIDTH', '_MAXWIDTH', '_PREFWIDTH'))}
rule('DiffPairsRouting', 'DiffPairsRouting', MINLIMIT=mil(0.15), MAXLIMIT=mil(0.5), MOSTFREQGAP=mil(0.2), **dp)
# Mask
rule('SolderMaskExpansion', 'SolderMaskExpansion-Via', 1, 'IsVia', EXPANSION=mil(0), ISTENTINGTOP='TRUE',
     ISTENTINGBOTTOM='TRUE', COMMENT='Tented vias (free option at JLCPCB and PCBWay)')
rule('SolderMaskExpansion', 'SolderMaskExpansion', 2, EXPANSION=mil(0.05), ISTENTINGTOP='FALSE',
     ISTENTINGBOTTOM='FALSE', COMMENT='0.05 mm keeps dams between fine-pitch pads')
rule('PasteMaskExpansion', 'PasteMaskExpansion', EXPANSION='0mil')
# Plane / polygon
rule('PlaneConnect', 'PlaneConnect')
rule('PlaneClearance', 'PlaneClearance')
pc = {f'{o}.{k}': v for o in ('THPAD', 'SMDPAD')
      for k, v in (('CONNECTSTYLE', 'Relief'), ('RELIEFCONDUCTORWIDTH', mil(0.3)), ('AIRGAPWIDTH', mil(0.25)))}
pc.update({'VIA.CONNECTSTYLE': 'Direct'})
rule('PolygonConnect', 'PolygonConnect', CONNECTSTYLE='Relief', RELIEFCONDUCTORWIDTH=mil(0.3),
     AIRGAPWIDTH=mil(0.25), RELIEFENTRIES='4', COMMENT='Pads: 0.3 mm spokes, vias direct', **pc)
# Manufacturing
rule('MinimumAnnularRing', 'MinimumAnnularRing', MINIMUMRING=mil(0.15), COMMENT='PCBWay minimum 0.15 mm') \
    if 'MinimumAnnularRing' in tmpl else None
rule('HoleSize', 'HoleSize', MINLIMIT=mil(0.3), MAXLIMIT=mil(6.0), ABSOLUTEVALUES='TRUE',
     COMMENT='0.3 mm keeps both fabs at base price; PCBWay max drill 6.0 mm')
rule('HoleToHoleClearance', 'HoleToHoleClearance-Vias', 1, 'IsVia', 'IsVia', GAP=mil(0.254),
     COMMENT='JLCPCB via hole-to-hole 0.2 mm')
rule('HoleToHoleClearance', 'HoleToHoleClearance', 2, GAP=mil(0.5),
     COMMENT='JLCPCB pad hole-to-hole 0.45 mm, PCBWay 16 mil')
rule('MinimumSolderMaskSliver', 'MinimumSolderMaskSliver', MINSOLDERMASKWIDTH=mil(0.1),
     COMMENT='Green mask; black/white mask needs 0.13 mm at JLCPCB')
rule('SilkToSolderMaskClearance', 'SilkToSolderMaskClearance', 1, 'IsPad', MINSILKSCREENTOMASKGAP=mil(0.15))
rule('SilkToSilkClearance', 'SilkToSilkClearance', SILKTOSILKCLEARANCE=mil(0.15))
rule('SilkToBoardRegionClearance', 'SilkToBoardRegionClearance')
rule('NetAntennae', 'NetAntennae')
rule('BoardOutlineClearance', 'BoardOutlineClearance', GAP=mil(0.3), GENERICCLEARANCE=mil(0.3),
     OBJECTCLEARANCES='', NETSCOPE='DifferentNets',
     COMMENT='Routed edge: JLCPCB 0.2 mm, PCBWay 0.25 mm. V-cut needs 0.4 mm')
# Placement
rule('ComponentClearance', 'ComponentClearance', GAP=mil(0.25))
rule('Height', 'Height')
# Testpoints / supply nets carried over from the board so "clear existing rules" loses nothing
for kind in ('FabricationTestpoint', 'FabricationTestPointUsage', 'AssemblyTestpoint',
             'AssemblyTestPointUsage', 'LayerPairs'):
    rule(kind, kind)
for r in board:
    if r['RULEKIND'] == 'SupplyNets':
        rules.append(r)

# MinimumAnnularRing has no template anywhere: build it from a plain record
if 'MinimumAnnularRing' not in tmpl:
    r = collections.OrderedDict(tmpl['HoleSize'])
    for k in ('MAXLIMIT', 'MINLIMIT', 'ABSOLUTEVALUES', 'MAXPERCENT', 'MINPERCENT'):
        r.pop(k, None)
    r.update(RULEKIND='MinimumAnnularRing', NAME='MinimumAnnularRing', PRIORITY='1', SCOPE1EXPRESSION='All',
             SCOPE2EXPRESSION='All', ENABLED='TRUE', UNIQUEID=uid(), COMMENT='PCBWay minimum 0.15 mm',
             MINIMUMRING=mil(0.15))
    rules.append(r)

with open(OUT + 'LowCost-2layer-JLCPCB-PCBWay.RUL', 'wb') as f:
    for r in rules:
        # every record ends in a pilcrow (0xB6) before CRLF; Altium rejects the file without it
        f.write(('|'.join(f'{k}={v}' for k, v in r.items()) + '\xb6\r\n').encode('latin1'))
print(len(rules), 'rules')

# ---- stackup ----
src = open(REF_STACK, encoding='utf-8-sig').read().strip('|').split('|')
kv = collections.OrderedDict(x.split('=', 1) for x in src)
OLD_SUB = kv['LAYERSUBSTACK_V8_0ID'].strip('{}')
doc, sub = '{%s}' % str(uuid.uuid4()).upper(), '{%s}' % str(uuid.uuid4()).upper()


def layer(idx, srcidx, **over):
    out = collections.OrderedDict()
    pre = f'LAYER_V8_{srcidx}'
    for k, v in kv.items():
        if k.startswith(pre) and not k[len(pre)].isdigit():
            nk = f'LAYER_V8_{idx}' + k[len(pre):].replace(OLD_SUB, sub.strip('{}'))
            out[nk] = v
    out[f'LAYER_V8_{idx}ID'] = '{%s}' % str(uuid.uuid4()).upper()
    for k, v in over.items():
        for full in list(out):
            if full == f'LAYER_V8_{idx}{k}' or full.endswith('}' + k) and full.startswith(f'LAYER_V8_{idx}_'):
                out[full] = v
    return out


core_mm = 1.6 - 2 * 0.035
layers = [
    layer(0, 0),                                     # Top Overlay
    layer(1, 1),                                     # Top Solder
    layer(2, 2, NAME='Top Layer'),                   # 1 oz
    layer(3, 5, NAME='Core', DIELTYPE='1', DIELHEIGHT=mil(core_mm), DIELCONST='4.5', DIELMATERIAL='FR-4',
          **{'$LSM$Thickness': mil(core_mm), '$LSM$Material': 'FR-4', '$LSM$DielectricConstant': '4.5'}),
    layer(4, 12, NAME='Bottom Layer'),               # 1 oz
    layer(5, 13),                                    # Bottom Solder
    layer(6, 14),                                    # Bottom Overlay
]
# drop the prepreg-specific material properties the core inherited from the 6-layer file
for k in [k for k in layers[3] if '$LSM$Material.' in k or '$LSM$LossTangent' in k]:
    del layers[3][k]
layers[3]['LAYER_V8_3LAYERID'] = '17039361'
top_id, bot_id = layers[2]['LAYER_V8_2ID'], layers[4]['LAYER_V8_4ID']

now = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')  # Altium parses this month-first
out = collections.OrderedDict()
for k, v in kv.items():
    if k.startswith(('LAYER_V8_', 'IMPEDANCEPROFILE', 'TRACEIMPEDANCE', 'VIASPAN', 'BRANCH')):
        continue
    out[k] = v
out.update(STACKUPDOCUMENTID=doc, STACKUPDOCUMENTREVISIONID='{%s}' % str(uuid.uuid4()).upper(),
           STACKUPDOCUMENTREVISIONDATE=now, LAYERMASTERSTACK_V8ID=doc, LAYERSUBSTACK_V8_0ID=sub,
           LAYERSUBSTACK_V8_0SYMMETRIC='True')
for L in layers:
    out.update(L)
vs = f'VIASPAN_V8_{sub}_0'
out.update({vs + 'ID': '{%s}' % str(uuid.uuid4()).upper(), vs + 'NAME': 'Thru 1:2', vs + 'TYPE': '0',
            vs + 'FIRSTLAYERID': top_id, vs + 'LASTLAYERID': bot_id, vs + 'SYMMETRIC': 'False'})
br, sec = '{%s}' % str(uuid.uuid4()).upper(), '{%s}' % str(uuid.uuid4()).upper()
out.update({'BRANCH_V8_0ID': br, 'BRANCH_V8_0NAME': 'Board',
            f'BRANCHSECTION_V8_{br}_0ID': sec, f'BRANCHSECTION_V8_{br}_0NAME': 'Branch Section-1'})
for k, v in kv.items():
    if k.startswith('BRANCHSECTIONSTACK_V8_'):
        nk = k.split('}_{', 1)[1].split('}_', 1)[1]
        out[f'BRANCHSECTIONSTACK_V8_{br}_{sec}_{nk}'] = v.replace('{' + OLD_SUB + '}', sub)
out[f'BRANCHSECTIONSTACK_V8_{br}_{sec}_0ID'] = '{%s}' % str(uuid.uuid4()).upper()

with open(OUT + 'LowCost-2layer-1.6mm.stackup', 'w', encoding='utf-8-sig', newline='') as f:
    f.write('|' + '|'.join(f'{k}={v}' for k, v in out.items()))
print(len(out), 'stackup keys')
