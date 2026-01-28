const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({});

const server = http.createServer((req, res) => {
    proxy.web(req, res, { target: 'http://127.0.0.1:8001' });
});

server.on('upgrade', (req, socket, head) => {
    proxy.ws(req, socket, head, { target: 'http://127.0.0.1:8001' });
});

proxy.on('error', (err, req, res) => {
    console.error('Proxy error:', err);
    if (res.writeHead) {
        res.writeHead(502, { 'Content-Type': 'text/plain' });
        res.end('Bad Gateway');
    }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`Proxy server running on port ${PORT}, forwarding to 8001`);
});
