"""Build JLCPCB/PCBWay (Gerber + NC Drill) and Aisler (ODB++) OutJobs by cloning known-good ones."""
import os, re

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + os.sep
DOC = 'PCB1.PcbDoc'
USBC = os.path.expanduser('~/git/usbc-pd-charger-st/usbc-pd-charger-st/usbc-pd-charger-st-gerber.OutJob')
AISLER = os.path.expanduser('~/git/bms-18s-hardware/OUT/push-to-aisler-odb.Outjob')

usbc = open(USBC, encoding='latin1').read().split('\n')
header = usbc[:usbc.index('[OutputGroup1]')]
cfg = {int(m.group(1)): m.group(2) for l in usbc for m in [re.match(r'Configuration(\d)_Item1=(.*)', l)] if m}


def setkeys(item, **kv):
    """Set every occurrence of each key (Altium repeats some keys) and insert missing ones in sorted position."""
    parts = item.split('|')
    for k, v in kv.items():
        hit = False
        for i, p in enumerate(parts):
            if p.split('=', 1)[0] == k:
                parts[i] = f'{k}={v}'
                hit = True
        if not hit:
            pos = next((i for i, p in enumerate(parts) if p.split('=', 1)[0] > k and not p.startswith(('Record=', 'DocumentPath='))), len(parts))
            parts.insert(pos, f'{k}={v}')
    return '|'.join(parts)


# 2-layer set: overlays, pastes, masks, top and bottom copper. The outline comes from the board shape.
LAYERS = [16973830, 16973832, 16973834, 16777217, 16842751, 16973835, 16973833, 16973831]
gerber = setkeys(cfg[2],
                 **{'Plot.Set': 'SerializeLayerHash.Version~2,ClassName~TPlotLayerStateArray,' + ','.join(f'{l}~1' for l in LAYERS)},
                 GerberUnit='Imperial', NumberOfDecimals='5', LeadingAndTrailingZeroesMode='SuppressLeadingZeroes',
                 OriginPosition='Relative', EmbeddedApertures='True', GenerateReports='False',
                 GenerateDRCRulesFile='False', MergePadAndRegion='False',
                 PlotBoardProfile='True', PlotBoardProfileFileName='PCB1.GM', DocumentPath=DOC)
drill = setkeys(cfg[3], Units='Imperial', NumberOfUnits='2', NumberOfDecimals='5',
                ZeroesMode='SuppressTrailingZeroes', OriginPosition='Relative',
                GenerateSeparatePlatedNonPlatedFiles='True', GenerateDrilledSlotsG85='True', DocumentPath=DOC)

PATH = r'.\Project Outputs for Nucleo-144-encoder\JLCPCB-PCBWay' + '\\'
jlc = header + f'''[OutputGroup1]
Name=JLCPCB-PCBWay Fabrication
Description=Gerber RS-274X (inch 2:5) and Excellon NC drill (inch 2:5), plated/non-plated split, for JLCPCB and PCBWay
TargetOutputMedium=JLCPCB-PCBWay
VariantName=[No Variations]
VariantScope=1
CurrentConfigurationName=
TargetPrinter=
PrinterOptions=Record=PrinterOptions|Copies=1|Duplex=1|TrueTypeOptions=3|Collate=1|PrintJobKind=1|PrintWhat=1
OutputMedium1=JLCPCB-PCBWay
OutputMedium1_Type=GeneratedFiles
OutputType1=Gerber
OutputName1=Gerber Files
OutputCategory1=Fabrication
OutputDocumentPath1={DOC}
OutputVariantName1=
OutputEnabled1=1
OutputEnabled1_OutputMedium1=1
OutputDefault1=0
Configuration1_Name1=OutputConfigurationParameter1
Configuration1_Item1={gerber}
OutputType2=NC Drill
OutputName2=NC Drill Files
OutputCategory2=Fabrication
OutputDocumentPath2={DOC}
OutputVariantName2=
OutputEnabled2=1
OutputEnabled2_OutputMedium1=2
OutputDefault2=0
Configuration2_Name1=OutputConfigurationParameter1
Configuration2_Item1={drill}
[PublishSettings]
OutputFilePath1={PATH}
ReleaseManaged1=0
OutputBasePath1=.\\Project Outputs for Nucleo-144-encoder\\
OutputPathMedia1=JLCPCB-PCBWay
OutputPathMediaValue1=JLCPCB-PCBWay
OutputPathOutputer1=[Output Type]
OutputPathOutputerPrefix1=
OutputPathOutputerValue1=
OutputFileName1=
OutputFileNameMulti1=
UseOutputNameForMulti1=1
OutputFileNameSpecial1=
OpenOutput1=0
[GeneratedFilesSettings]
RelativeOutputPath1={PATH}
OpenOutputs1=0
AddToProject1=0
TimestampFolder1=0
UseOutputName1=0
OpenODBOutput1=0
OpenGerberOutput1=0
OpenNCDrillOutput1=0
OpenIPCOutput1=0
EnableReload1=0
'''.split('\n')

with open(OUT + 'JLCPCB-PCBWay-Fabrication.OutJob', 'w', encoding='latin1', newline='\n') as f:
    f.write('\n'.join(jlc) + '\n')

# Aisler: the bms-18s job verbatim (Push to AISLER + ODB++ folder), pointed at this board.
a = open(AISLER, encoding='latin1').read()
a = a.replace('OutputDocumentPath1=\n', f'OutputDocumentPath1={DOC}\n', 1)
a = re.sub(r'(Configuration1_Item1=.*?)\|DocumentPath=[^\n|]*', lambda m: m.group(1) + f'|DocumentPath={DOC}', a)
a = a.replace('[OutputGroup1]\nName=\n', '[OutputGroup1]\nName=Aisler ODB++\n', 1)
with open(OUT + 'Aisler-ODB.OutJob', 'w', encoding='latin1', newline='\n') as f:
    f.write(a)
print('ok')
