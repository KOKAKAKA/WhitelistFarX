const express = require('express');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const { initializeServer, monitorServer, cacheMiddleware } = require('./utils');
const { checkServerReady } = require('./middlewares');
const routes = require('./routes');

const app = express();
const port = 18635;

app.set('trust proxy', 1);

const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 6000,
  standardHeaders: true,
  legacyHeaders: false,
});

app.use(limiter);
app.use(express.json());
app.use(morgan('combined'));
app.use(checkServerReady);
app.use(cacheMiddleware);
app.use('/', routes);

app.listen(port, () => {
  console.log(`Server started at http://localhost:${port}`);
  initializeServer().then(() => {
    monitorServer();
  }).catch(err => {
    console.error('Error initializing server:', err);
  });
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM. Shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('Received SIGINT. Shutting down gracefully...');
  process.exit(0);
});
