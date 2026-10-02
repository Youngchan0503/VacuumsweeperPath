import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://air.daegu.go.kr/cmsh/air.daegu.go.kr/js/main.js', headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, context=ctx, timeout=10)
js = resp.read().decode('utf-8', errors='ignore')
print("main.js length:", len(js))
print(js[:2000])
