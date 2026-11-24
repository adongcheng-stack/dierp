import glob
import re

import yaml

t = open('ontology/src/erp-ontology.ttl', encoding='utf-8').read()
cls = set(re.findall(r'^:(\w+)\s+a\s+owl:Class', t, re.M))
y = {}
for f in ['planning', 'admin', 'dashboard']:
    m = yaml.safe_load(open(f'ontology/model/{f}.yaml', encoding='utf-8'))
    for k, v in m['entities'].items():
        y[k] = v['table']
tables = set()
for p in glob.glob('backend/common/models/*.py'):
    s = open(p, encoding='utf-8').read()
    tables |= set(re.findall(r'__tablename__\s*=\s*["\']([^"\']+)', s))
print('total tables', len(tables))
print('yaml tables', len(set(y.values())))
unt = sorted(tables - set(y.values()))
print('uncovered tables', len(unt))
print(unt)
print()
print('classes not in yaml', sorted(cls - set(y)))
