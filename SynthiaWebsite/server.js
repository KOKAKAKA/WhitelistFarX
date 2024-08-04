const express = require('express');
const path = require('path');
const compression = require('compression');
const app = express();
const port = 18635;

// Middleware to compress responses
app.use(compression());

// Serve static files from the 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// Basic health check endpoint
app.get('/health', (req, res) => {
    res.send('Server is running');
});

// Start the server
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
