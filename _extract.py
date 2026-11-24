import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
s = open(r'D:\project\erp\DIERP-demo.html', encoding='utf-8').read()
print(s[1403000:1411000])
