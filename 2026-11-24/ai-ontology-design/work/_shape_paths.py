import re

t = open('ontology/src/shapes.ttl', encoding='utf-8').read()
blocks = re.split(r'\n(?=:[A-Za-z0-9_]+Shape a sh:NodeShape)', t)
want = {'Forecast', 'MpsPlan', 'MrpRun', 'PlannedOrder', 'PurchaseOrder', 'ScheduleRun',
        'ProductionOrder', 'SalesOrder', 'Material', 'KittingResult', 'MrpException',
        'NonConformanceReport', 'SalesInvoice', 'Customer'}
for b in blocks:
    m = re.match(r':(\w+)Shape a sh:NodeShape', b)
    if not m:
        continue
    tc = re.search(r'sh:targetClass :(\w+)', b)
    if not tc or tc.group(1) not in want:
        continue
    name = tc.group(1)
    paths = sorted(set(re.findall(r'sh:path :(\w+)', b)))
    print(f"{name}Shape -> {name}: {paths}")
