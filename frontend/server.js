const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

// Enable trust proxy for proper forwarding
app.set('trust proxy', true);

// Proxy all requests to Django backend
app.use('/', createProxyMiddleware({
    target: 'http://127.0.0.1:8001',
    changeOrigin: false,
    ws: true,
    xfwd: true,
    onProxyRes: (proxyRes, req, res) => {
        console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} -> ${proxyRes.statusCode}`);
    },
    onError: (err, req, res) => {
        console.error('Proxy error:', err.message);
        res.status(502).send('Proxy Error');
    }
}));

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Express proxy server running on port ${PORT}`);
});
