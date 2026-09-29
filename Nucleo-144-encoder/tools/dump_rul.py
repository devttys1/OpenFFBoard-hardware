"""Print the dimensional fields of every rule in one or more Altium .RUL files.

    python3 dump_rul.py FILE.RUL [...]
"""
import sys
KEYS=('RULEKIND','NAME','ENABLED','PRIORITY','NETSCOPE','LAYERKIND','SCOPE1EXPRESSION','SCOPE2EXPRESSION','GAP','MINLIMIT','MAXLIMIT','PREFEREDWIDTH','MINWIDTH','MAXWIDTH','WIDTH','MINHOLEWIDTH','MAXHOLEWIDTH','HOLEWIDTH','EXPANSION','MINSOLDERMASKWIDTH','MINSILKSCREENTOMASKGAP','CLEARANCE','AIRGAPWIDTH','RELIEFCONDUCTORWIDTH','CONNECTSTYLE','MINIMUMRING','ISTENTINGTOP','ISTENTINGBOTTOM','USEPASTESMD','SILKTOSILKCLEARANCE','GAPSILK','ABSOLUTEVALUES','MINIMUM','MAXIMUM','OBJECTCLEARANCES','RELIEFENTRIES','IGNOREPADTOPADCLEARANCEINFOOTPRINT','ALLOWEDPLATEDHOLES','USESOLDERMASKEXPANSIONFROMTHEPAD','GAP','ALLOWSAMECOMPONENT')
for f in sys.argv[1:]:
    print('#####',f)
    d=open(f,'rb').read().decode('latin1')
    for line in d.replace('\r','').split('\n'):
        line=line.strip().strip('\x00\xa0')
        if 'RULEKIND' not in line: continue
        kv=dict(x.split('=',1) for x in line.strip('|').split('|') if '=' in x)
        print('  '+' | '.join(f"{k}={kv[k][:90]}" for k in KEYS if k in kv and kv[k].strip()))
