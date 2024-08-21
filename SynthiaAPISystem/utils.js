const { exec } = require('child_process');
const process = require('process');
const os = require('os');
const NodeCache = require('node-cache');
const { promisify } = require('util');
const execAsync = promisify(exec);

const cache = new NodeCache({ stdTTL: 60, checkperiod: 120 });
let serverReady = false;

// Function to check if the server is ready
function isServerReady() {
  return serverReady;
}

// Function to set the server ready status
function setServerReady(status) {
  serverReady = status;
}

// Function to initialize the server
async function initializeServer() {
  try {
    // Perform any asynchronous initialization tasks here
    setServerReady(true);
    console.log('Server is fully initialized and ready to handle requests.');
  } catch (error) {
    console.error(`Error during server initialization: ${error.message}`);
  }
}

// Function to restart the server
async function restartServer() {
  try {
    console.log('Restarting server.');
    await execAsync('node restart.js');
    process.exit(); // Exit current process to restart
  } catch (error) {
    console.error(`Error executing restart script: ${error.message}`);
  }
}

// Function to clear the cache
function clearCache() {
  console.log('Clearing cache');
  cache.flushAll();
}

// Function to monitor server health and perform optimizations
function monitorServer() {
  setInterval(async () => {
    const freeMemory = os.freemem();
    const totalMemory = os.totalmem();
    const memoryUsage = ((totalMemory - freeMemory) / totalMemory) * 100;

    // If memory usage exceeds 80%, clear the cache
    if (memoryUsage > 80) {
      console.log('High memory usage detected, clearing cache.');
      clearCache();
    }

    // Restart the server if uptime exceeds 24 hours
    if (process.uptime() > 24 * 60 * 60) {
      console.log('Uptime exceeded 24 hours, restarting server.');
      await restartServer();
    }
  }, 5 * 60 * 1000); // Check every 5 minutes (increased frequency)
}

// Middleware to cache responses for GET requests
function cacheMiddleware(req, res, next) {
  if (req.method === 'GET') {
    const key = req.originalUrl || req.url;
    const cachedResponse = cache.get(key);
    if (cachedResponse) {
      return res.json(cachedResponse);
    } else {
      res.originalJson = res.json;
      res.json = (body) => {
        cache.set(key, body);
        res.originalJson(body);
      };
    }
  }
  next();
}

// Additional optimization: Run CPU-intensive tasks asynchronously
function asyncTask(task, ...args) {
  return new Promise((resolve, reject) => {
    setImmediate(async () => {
      try {
        const result = await task(...args);
        resolve(result);
      } catch (error) {
        reject(error);
      }
    });
  });
}

module.exports = { initializeServer, restartServer, clearCache, monitorServer, isServerReady, cacheMiddleware, asyncTask };
