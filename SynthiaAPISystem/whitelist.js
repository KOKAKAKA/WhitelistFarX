const express = require('express');
const fs = require('fs/promises');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const NodeCache = require('node-cache');
const AsyncLock = require('async-lock');
const { exec } = require('child_process');
const process = require('process');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const os = require('os');

const app = express();
const port = 18635;
const cache = new NodeCache({ stdTTL: 60, checkperiod: 120 });
const lock = new AsyncLock();
const restartScriptPath = 'restart.js';

let serverReady = false;

app.set('trust proxy', 1);

// Middleware for JSON parsing and logging
app.use(express.json());
app.use(morgan('combined'));

// Rate limiting middleware to allow 100 requests per second
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 6000, // limit each IP to 6000 requests per windowMs
});
app.use(limiter);

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
      await fs.mkdir(path.dirname(filePath), { recursive: true }); // Ensure directory exists
      await fs.writeFile(filePath, JSON.stringify(data, null, 2));
      cache.set(filePath, data);
    } catch (error) {
      console.error(`Error writing file: ${error.message}`);
    }
  });
}

// Middleware to handle server initialization
app.use((req, res, next) => {
  if (!serverReady) {
    res.status(503).json({ success: false, message: 'Server is warming up, please try again later.' });
  } else {
    next();
  }
});

// Endpoint to generate a new key for a specific user
app.post('/generate-key/:username', async (req, res) => {
  const { username } = req.params;
  try {
    const newKey = uuidv4();
    const userKeyPath = path.join(__dirname, 'StoredKey', username, 'keys.json');
    const storedKeys = await readJson(userKeyPath);
    storedKeys[newKey] = 'Nil';
    await writeJson(userKeyPath, storedKeys);
    res.json({ success: true, key: newKey });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Endpoint to update HWID for a specific user and key
app.get('/update-hwid/:username', async (req, res) => {
  const { username } = req.params;
  const { key, hwid } = req.query;
  try {
    const userKeyPath = path.join(__dirname, 'StoredKey', username, 'keys.json');
    const storedKeys = await readJson(userKeyPath);
    if (!storedKeys[key]) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }
    if (storedKeys[key] !== 'Nil') {
      return res.status(400).json({ success: false, message: 'HWID already set' });
    }
    storedKeys[key] = hwid;
    await writeJson(userKeyPath, storedKeys);
    res.json({ success: true, message: 'HWID updated successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Endpoint to reset HWID for a given user and key
app.post('/reset-hwid/:username', async (req, res) => {
  const { username } = req.params;
  const { key } = req.body;
  try {
    const userKeyPath = path.join(__dirname, 'StoredKey', username, 'keys.json');
    const storedKeys = await readJson(userKeyPath);
    if (!storedKeys[key]) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }
    storedKeys[key] = 'Nil';
    await writeJson(userKeyPath, storedKeys);
    res.json({ success: true, message: 'HWID reset successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Endpoint to delete a key for a specific user
app.post('/delete-key/:username', async (req, res) => {
  const { username } = req.params;
  const { key } = req.body;
  try {
    const userKeyPath = path.join(__dirname, 'StoredKey', username, 'keys.json');
    const storedKeys = await readJson(userKeyPath);
    if (!storedKeys[key]) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }
    delete storedKeys[key];
    await writeJson(userKeyPath, storedKeys);
    res.json({ success: true, message: 'Key deleted successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Endpoint to fetch all keys and HWIDs for a specific user as Lua table string
app.get('/fetch-keys-hwids/:username', async (req, res) => {
  const { username } = req.params;
  try {
    const userKeyPath = path.join(__dirname, 'StoredKey', username, 'keys.json');
    const storedKeys = await readJson(userKeyPath);
    const luaTableString = "return " + JSON.stringify(storedKeys).replace(/"(\w+)":/g, '$1:').replace(/"/g, "'");
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(luaTableString);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Endpoint to fetch keys and HWIDs as a Lua script for a specific user
app.get('/KeyRaw/:username', async (req, res) => {
  const { username } = req.params;
  try {
    const userKeyPath = path.join(__dirname, 'StoredKey', username, 'keys.json');
    const storedKeys = await readJson(userKeyPath);
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

// Function to initialize the server
async function initializeServer() {
  try {
    serverReady = true;
    console.log('Server is fully initialized and ready to handle requests.');
  } catch (error) {
    console.error(`Error during server initialization: ${error.message}`);
  }
}

// Function to restart the server
function restartServer() {
  console.log('Restarting server.');
  setTimeout(() => {
    exec(`node ${restartScriptPath}`, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error executing restart script: ${error.message}`);
        return;
      }
      if (stderr) {
        console.error(`Restart script stderr: ${stderr}`);
      }
      console.log(`Restart script stdout: ${stdout}`);
    });
    process.exit();
  }, 1000); // 1-second delay
}

// Function to clear cache
function clearCache() {
  console.log('Clearing cache');
  cache.flushAll();
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.send('Server is running');
});

// Monitor and manage server performance
function monitorServer() {
  setInterval(async () => {
    const freeMemory = os.freemem();
    const totalMemory = os.totalmem();
    const memoryUsage = ((totalMemory - freeMemory) / totalMemory) * 100;

    if (memoryUsage > 80) {
      console.log('High memory usage detected, clearing cache.');
      clearCache();
    }

    if (process.uptime() > 1 * 30 * 60) {
      console.log('Uptime exceeded 24 hours, restarting server.');
      restartServer();
    }
  }, 5 * 60 * 1000); // Every 10 minutes
}

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
  initializeServer().then(() => {
    monitorServer(); // Start the monitoring only after initialization
  });
});
