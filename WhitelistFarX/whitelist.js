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
const storedKeyPath = path.join(__dirname, 'StoredKey.json');
const whitelistedUserPath = path.join('/storage/emulated/0/download/TermuxS', 'WhitelistedUser.json');
const cache = new NodeCache({ stdTTL: 60, checkperiod: 120 });
const lock = new AsyncLock();
const restartScriptPath = path.join(__dirname, 'restart.js');

let serverReady = false;

// Middleware for JSON parsing and logging
app.use(express.json());
app.use(morgan('combined'));

// Rate limiting middleware to prevent abuse
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
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
      console.error(`Error reading file from ${filePath}: ${error.message}`);
      return {};
    }
  });
}

// Utility function to write JSON file with locking
async function writeJson(filePath, data) {
  return lock.acquire('fileLock', async () => {
    try {
      await fs.writeFile(filePath, JSON.stringify(data, null, 2));
      cache.set(filePath, data);
    } catch (error) {
      console.error(`Error writing file to ${filePath}: ${error.message}`);
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

// Endpoint to generate a new key
app.post('/generate-key', async (req, res) => {
  try {
    const newKey = uuidv4();
    const storedKeys = await readJson(storedKeyPath);
    storedKeys[newKey] = 'Nil';
    await writeJson(storedKeyPath, storedKeys);
    res.json({ success: true, key: newKey });
  } catch (error) {
    res.status(500).json({ success: false, message: `Error generating key: ${error.message}` });
  }
});

// Endpoint to update HWID for a given key
app.get('/update-hwid', async (req, res) => {
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
    res.status(500).json({ success: false, message: `Error updating HWID: ${error.message}` });
  }
});

// Endpoint to reset HWID for a given key
app.post('/reset-hwid', async (req, res) => {
  const { key } = req.body;
  try {
    const storedKeys = await readJson(storedKeyPath);
    if (!storedKeys[key]) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }
    storedKeys[key] = 'Nil';
    await writeJson(storedKeyPath, storedKeys);
    res.json({ success: true, message: 'HWID reset successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: `Error resetting HWID: ${error.message}` });
  }
});

// Endpoint to delete a key
app.post('/delete-key', async (req, res) => {
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
    res.status(500).json({ success: false, message: `Error deleting key: ${error.message}` });
  }
});

// Endpoint to fetch all keys and HWIDs as Lua table string
app.get('/fetch-keys-hwids', async (req, res) => {
  try {
    const storedKeys = await readJson(storedKeyPath);
    const luaTableString = "return " + JSON.stringify(storedKeys).replace(/"(\w+)":/g, '$1:').replace(/"/g, "'");
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(luaTableString);
  } catch (error) {
    res.status(500).json({ success: false, message: `Error fetching keys and HWIDs: ${error.message}` });
  }
});

// Endpoint to fetch keys and HWIDs as a Lua script
app.get('/KeyRaw', async (req, res) => {
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
    res.status(500).json({ success: false, message: `Error fetching keys and HWIDs as Lua script: ${error.message}` });
  }
});

// Endpoint to get the profile of a whitelisted user
app.get('/profile', async (req, res) => {
  const { userid } = req.query;
  try {
    const storedUsers = await readJson(whitelistedUserPath);
    const userProfile = storedUsers[userid];
    if (!userProfile) {
      return res.status(404).json({ success: false, message: 'User profile not found' });
    }
    res.json({ success: true, profile: userProfile });
  } catch (error) {
    res.status(500).json({ success: false, message: `Error fetching user profile: ${error.message}` });
  }
});

// Function to initialize the server
async function initializeServer() {
  try {
    await readJson(storedKeyPath);
    await readJson(whitelistedUserPath);
    serverReady = true;
    console.log('Server is fully initialized and ready to handle requests.');
  } catch (error) {
    console.error(`Error during server initialization: ${error.message}`);
  }
}

// Function to restart the server
function restartServer() {
  console.log('Restarting server.');
  exec(`node ${restartScriptPath}`, (error, stdout, stderr) => {
    if (error) {
      console.error(`Error executing restart script: ${error.message}`);
    }
    if (stderr) {
      console.error(`Restart script stderr: ${stderr}`);
    }
    console.log(`Restart script stdout: ${stdout}`);
  });
  process.exit();
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

    if (process.uptime() > 24 * 60 * 60) {
      console.log('Uptime exceeded 24 hours, restarting server.');
      restartServer();
    }
  }, 10 * 60 * 1000); // Every 10 minutes
}

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
  initializeServer().then(() => {
    monitorServer();
  });
});
