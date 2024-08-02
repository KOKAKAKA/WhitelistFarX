const express = require('express');
const fs = require('fs/promises');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const NodeCache = require('node-cache');
const AsyncLock = require('async-lock');
const { exec } = require('child_process');

const app = express();
const port = 18635;
const storedKeyPath = path.join(__dirname, 'StoredKey.json');
const cache = new NodeCache({ stdTTL: 60 });
const lock = new AsyncLock();
const endpointHandlers = {};
const readyCheckMap = new Map();

const RELOAD_INTERVAL = 10 * 60 * 1000; // 10 minutes
const RELOAD_DELAY = 1000; // 1 second

const endpointsToLoad = [
  '/generate-key',
  '/update-hwid',
  '/reset-hwid',
  '/delete-key',
  '/fetch-keys-hwids',
  '/KeyRaw'
];

// Utility function to read JSON file with locking
async function readJson(filePath) {
  return lock.acquire('fileLock', async () => {
    if (cache.has(filePath)) {
      return cache.get(filePath);
    }
    try {
      const data = await fs.readFile(filePath, 'utf8');
      const jsonData = JSON.parse(data);
      cache.set(filePath, jsonData);
      return jsonData;
    } catch (error) {
      console.error(`Error reading file: ${error.message}`);
      return {};
    }
  });
}

// Utility function to write JSON file with locking
async function writeJson(filePath, data) {
  return lock.acquire('fileLock', async () => {
    try {
      await fs.writeFile(filePath, JSON.stringify(data, null, 2));
      cache.set(filePath, data); // Update cache on successful write
    } catch (error) {
      console.error(`Error writing file: ${error.message}`);
    }
  });
}

// Function to clear the cache
function clearCache() {
  console.log('Clearing cache.');
  cache.flushAll(); // Clear all items in the cache
}

// Function to load an endpoint handler
async function loadEndpointHandler(endpoint, handler) {
  endpointHandlers[endpoint] = handler;
  readyCheckMap.set(endpoint, true); // Set the endpoint as ready
  console.log(`Loading handler for ${endpoint}`);
}

// Function to unload an endpoint handler
function unloadEndpointHandler(endpoint) {
  console.log(`Unloading handler for ${endpoint}`);
  delete endpointHandlers[endpoint];
  readyCheckMap.set(endpoint, false); // Set the endpoint as not ready
}

// Middleware to dynamically load and use endpoint handlers
app.use(async (req, res, next) => {
  const endpoint = req.path;

  if (readyCheckMap.get(endpoint)) {
    // Use the loaded handler
    endpointHandlers[endpoint](req, res, next);
  } else {
    res.status(404).send('Not Found');
  }
});

// Load all handlers at startup
async function loadAllHandlers() {
  await loadEndpointHandler('/generate-key', async (req, res) => {
    try {
      const newKey = uuidv4(); // Generate a new UUID
      const storedKeys = await readJson(storedKeyPath);
      storedKeys[newKey] = 'Nil'; // Set HWID to 'Nil'
      await writeJson(storedKeyPath, storedKeys);
      res.json({ success: true, key: newKey });
    } catch (error) {
      res.status(500).json({ success: false, message: error.message });
    }
  });

  await loadEndpointHandler('/update-hwid', async (req, res) => {
    const { key, hwid } = req.query;
    try {
      const storedKeys = await readJson(storedKeyPath);
      if (!storedKeys[key]) {
        return res.status(400).json({ success: false, message: 'Key not found' });
      }
      if (storedKeys[key] !== 'Nil') {
        return res.status(400).json({ success: false, message: 'HWID already set' });
      }
      storedKeys[key] = hwid;
      await writeJson(storedKeyPath, storedKeys);
      res.json({ success: true, message: 'HWID updated successfully' });
    } catch (error) {
      res.status(500).json({ success: false, message: error.message });
    }
  });

  await loadEndpointHandler('/reset-hwid', async (req, res) => {
    const { key } = req.body;
    try {
      const storedKeys = await readJson(storedKeyPath);
      if (!storedKeys[key]) {
        return res.status(400).json({ success: false, message: 'Key not found' });
      }
      storedKeys[key] = 'Nil'; // Reset HWID for the key
      await writeJson(storedKeyPath, storedKeys);
      res.json({ success: true, message: 'HWID reset successfully' });
    } catch (error) {
      res.status(500).json({ success: false, message: error.message });
    }
  });

  await loadEndpointHandler('/delete-key', async (req, res) => {
    const { key } = req.body;
    try {
      const storedKeys = await readJson(storedKeyPath);
      if (!storedKeys[key]) {
        return res.status(400).json({ success: false, message: 'Key not found' });
      }
      delete storedKeys[key];
      await writeJson(storedKeyPath, storedKeys);
      res.json({ success: true, message: 'Key deleted successfully' });
    } catch (error) {
      res.status(500).json({ success: false, message: error.message });
    }
  });

  await loadEndpointHandler('/fetch-keys-hwids', async (req, res) => {
    try {
      const storedKeys = await readJson(storedKeyPath);
      const luaTableString = "return " + JSON.stringify(storedKeys).replace(/"(\w+)":/g, '$1:').replace(/"/g, "'");
      res.setHeader('Cache-Control', 'no-store');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
      res.send(luaTableString);
    } catch (error) {
      res.status(500).json({ success: false, message: error.message });
    }
  });

  await loadEndpointHandler('/KeyRaw', async (req, res) => {
    try {
      const storedKeys = await readJson(storedKeyPath);
      let luaTableString = "local KeysAndHwid = {\n";
      for (const [key, hwid] of Object.entries(storedKeys)) {
        luaTableString += `    ["${key}"] = "${hwid}",\n`;
      }
      luaTableString += "}\n\nreturn KeysAndHwid";
      res.setHeader('Cache-Control', 'no-store');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
      res.type('text/plain');
      res.send(luaTableString);
    } catch (error) {
      res.status(500).json({ success: false, message: error.message });
    }
  });
}

// Function to measure server ping
function measurePing(callback) {
  const startTime = Date.now();
  exec('ping -c 1 localhost', (error, stdout, stderr) => {
    if (error) {
      console.error(`Ping error: ${stderr}`);
      callback(5000); // Return a high ping value on error
    } else {
      const endTime = Date.now();
      callback(endTime - startTime);
    }
  });
}

// Function to periodically reload handlers
async function periodicReload() {
  setInterval(async () => {
    measurePing(async (ping) => {
      if (ping > 5000) {
        console.log('High ping detected, resetting all endpoints.');
        for (const endpoint of endpointsToLoad) {
          unloadEndpointHandler(endpoint);
        }
        await new Promise(resolve => setTimeout(resolve, RELOAD_DELAY));
        clearCache();
        await loadAllHandlers();
      } else {
        console.log(`Ping: ${ping} ms`);
        for (const endpoint of endpointsToLoad) {
          unloadEndpointHandler(endpoint);
          await new Promise(resolve => setTimeout(resolve, RELOAD_DELAY));
          clearCache();
          await loadAllHandlers();
        }
      }
    });
  }, RELOAD_INTERVAL);
}

// Start the server
app.listen(port, async () => {
  console.log(`Server running at http://localhost:${port}`);
  await loadAllHandlers();
  periodicReload();
});
