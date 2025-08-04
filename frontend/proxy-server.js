// proxy-server.js
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = 9000; // The port our proxy will listen on
const FRONTEND_TARGET = 'http://localhost:8080'; // Where 'serve' is running
const BACKEND_TARGET = 'http://localhost:8000'; // Where 'uvicorn' is running

console.log(`Proxy server starting...`);
console.log(`- Forwarding /api requests to: ${BACKEND_TARGET}`);
console.log(`- Forwarding other requests to: ${FRONTEND_TARGET}`);

// Proxy /api requests to the backend
app.use('/api', createProxyMiddleware({
    target: BACKEND_TARGET,
    changeOrigin: true, // Recommended for virtual hosted sites
    pathRewrite: {'^/api' : ''}, // Remove /api prefix before forwarding
    onError: (err, req, res) => {
        console.error('Proxy Error (Backend):', err);
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Proxy error occurred while connecting to the backend.');
    }
}));

// Proxy all other requests to the frontend static server
app.use('/', createProxyMiddleware({
    target: FRONTEND_TARGET,
    changeOrigin: true,
    onError: (err, req, res) => {
        console.error('Proxy Error (Frontend):', err);
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Proxy error occurred while connecting to the frontend server.');
    }
}));

app.listen(PORT, '0.0.0.0', () => { // Listen on all interfaces
    console.log(`\nProxy server listening on http://localhost:${PORT}`);
    console.log(`Point your ngrok tunnel to this port: ngrok http ${PORT}`);
});