import json
import re

m = json.load(open('ontology/src/mappings.json', encoding='utf-8'))
print('enums', len(m['enumerations']))
print('enum values', sum(len(v) for v in m['enumerations'].values()))
t = open('ontology/src/erp-ontology.ttl', encoding='utf-8').read()
print('datatype props', len(re.findall(r'a owl:DatatypeProperty', t)))
print('object props', len(re.findall(r'a owl:ObjectProperty', t)))
s = open('ontology/src/shapes.ttl', encoding='utf-8').read()
print('node shapes', len(re.findall(r'a sh:NodeShape', s)))
print('sh:in lists', len(re.findall(r'sh:in \(', s)))
