const express = require('express');
const fs = require('fs/promises');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const NodeCache = require('node-cache');
const AsyncLock = require('async-lock');
const { exec } = require('child_process');
const process = require('process');

const app = express();
const port = 18635;
const storedKeyPath = path.join(__dirname, 'StoredKey.json');
const restartScriptPath = path.join(__dirname, 'restart.js'); // Path to the restart script

// Initialize cache with a time-to-live of 60 seconds
const cache = new NodeCache({ stdTTL: 60 });

// Create a lock instance to manage concurrent access
const lock = new AsyncLock();

// Flag to track if initialization has occurred
let initialized = false;
let idleTimeout;

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

// Function to restart the server after inactivity
function restartServer() {
  console.log('Restarting server due to inactivity.');

  // Introduce a delay before running the restart script
  setTimeout(() => {
    // Execute restart.js script
    exec(`node ${restartScriptPath}`, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error executing restart script: ${error.message}`);
        return;
      }
      if (stderr) {
        console.error(`Restart script stderr: ${stderr}`);
        return;
      }
      console.log(`Restart script stdout: ${stdout}`);
    });

    // Exit the current process
    process.exit();
  }, 500); // 2-second delay before running the restart script
}

// Middleware to initialize server data if not already initialized
app.use(async (req, res, next) => {
  if (!initialized) {
    await initializeData();
    initialized = true;
  }
  resetIdleTimeout(); // Reset idle timer on each request
  next();
});

async function initializeData() {
  try {
    await readJson(storedKeyPath);
    console.log('Server initialized and data loaded.');
  } catch (error) {
    console.error('Error during initialization:', error.message);
  }
}

function resetIdleTimeout() {
  clearTimeout(idleTimeout);
  idleTimeout = setTimeout(restartServer, 1500); // 5 seconds of inactivity
}

// Endpoint to generate a new key
app.post('/generate-key', async (req, res) => {
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
    res.status(500).json({ success: false, message: error.message });
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
    storedKeys[key] = 'Nil'; // Reset HWID for the key
    await writeJson(storedKeyPath, storedKeys);
    res.json({ success: true, message: 'HWID reset successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
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
    res.status(500).json({ success: false, message: error.message });
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
    res.status(500).json({ success: false, message: error.message });
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
    res.status(500).json({ success: false, message: error.message });
  }
});

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
