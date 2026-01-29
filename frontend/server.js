const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

// Enable trust proxy for proper forwarding
app.set('trust proxy', true);

// Logging middleware
app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] INCOMING: ${req.method} ${req.url}`);
    console.log(`  Headers: ${JSON.stringify(req.headers)}`);
    next();
});

// Proxy all requests to Django backend
app.use('/', createProxyMiddleware({
    target: 'http://127.0.0.1:8001',
    changeOrigin: false,
    ws: true,
    xfwd: true,
    onProxyReq: (proxyReq, req, res) => {
        console.log(`[${new Date().toISOString()}] PROXY REQ: ${req.method} ${req.url}`);
    },
    onProxyRes: (proxyRes, req, res) => {
        const size = proxyRes.headers['content-length'] || 'unknown';
        console.log(`[${new Date().toISOString()}] PROXY RES: ${proxyRes.statusCode} - Size: ${size} for ${req.url}`);
    },
    onError: (err, req, res) => {
        console.error(`[${new Date().toISOString()}] PROXY ERROR: ${err.message}`);
        if (!res.headersSent) {
            res.status(502).send('Proxy Error');
        }
    }
}));

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Express proxy server running on port ${PORT}`);
});
