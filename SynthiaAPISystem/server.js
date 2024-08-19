const express = require('express');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const { initializeServer, monitorServer } = require('./utils');
const { checkServerReady } = require('./middlewares');
const routes = require('./routes');
const app = express();
const port = 18635;

app.set('trust proxy', 1);

// Rate limiting middleware
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 6000, // limit each IP to 6000 requests per windowMs
});
app.use(limiter);

// Middleware for JSON parsing and logging
app.use(express.json());
app.use(morgan('combined'));

// Middleware for server readiness
app.use(checkServerReady);

// API routes
app.use('/', routes);

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
  initializeServer().then(() => {
    monitorServer(); // Start the monitoring after initialization
  });
});
