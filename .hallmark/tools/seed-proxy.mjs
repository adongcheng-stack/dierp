import http from 'node:http';

const ORIGIN = 'http://localhost:3100';
const PORT = 3101;
const SEED = `<script>try{localStorage.setItem('auth-storage',JSON.stringify({state:{token:'mock.admin',user:{username:'admin',email:'admin@hserp.com',full_name:'系统管理员',role:'ADMIN',department:'IT'},isAuthenticated:true},version:0}))}catch(e){}</script>`;

http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', ORIGIN);
  try {
    const upstream = await fetch(`${ORIGIN}${url.pathname}${url.search}`, {
      method: req.method,
      headers: { ...req.headers, host: 'localhost:3100' },
      body: ['GET', 'HEAD'].includes(req.method || '') ? undefined : await new Promise((resolve) => {
        const chunks = [];
        req.on('data', (c) => chunks.push(c));
        req.on('end', () => resolve(Buffer.concat(chunks)));
      }),
      redirect: 'manual',
    });
    const headers = {};
    upstream.headers.forEach((value, key) => {
      if (!['content-length', 'content-encoding', 'transfer-encoding', 'connection'].includes(key)) headers[key] = value;
    });
    let body = Buffer.from(await upstream.arrayBuffer());
    if (url.pathname === '/' && (headers['content-type'] || '').includes('text/html')) {
      body = Buffer.from(body.toString('utf8').replace('</head>', `${SEED}</head>`));
    }
    res.writeHead(upstream.status, headers);
    res.end(body);
  } catch (error) {
    res.writeHead(502);
    res.end(String(error));
  }
}).listen(PORT, () => console.log(`preview proxy on http://localhost:${PORT}`));
