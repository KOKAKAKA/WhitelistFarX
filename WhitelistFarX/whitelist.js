const express = require('express');
const fs = require('fs').promises; // Use promises-based fs
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const cluster = require('cluster');
const os = require('os');
const axios = require('axios'); // For warm-up script

const app = express();
const port = 18635;
const numCPUs = Math.max(1, os.cpus().length - 1); // Number of workers to use

// Paths to JSON file
const storedKeyPath = path.join(__dirname, 'StoredKey.json');

// Serve static files from the current directory
app.use(express.static(__dirname));
app.use(express.json()); // To parse JSON bodies

let cachedKeys = null;

// Function to read JSON data asynchronously with caching
const readJsonAsync = async (filePath) => {
    if (cachedKeys) return cachedKeys;

    try {
        const data = await fs.readFile(filePath, 'utf8');
        cachedKeys = JSON.parse(data);
        return cachedKeys;
    } catch (error) {
        throw new Error('Error reading JSON file');
    }
};

// Function to write JSON data asynchronously with caching update
const writeJsonAsync = async (filePath, data) => {
    try {
        await fs.writeFile(filePath, JSON.stringify(data, null, 2));
        cachedKeys = data; // Update cache after writing
    } catch (error) {
        throw new Error('Error writing JSON file');
    }
};

// Warm-up function to preload data or perform initial requests
const warmUpServer = async () => {
    try {
        await axios.post('http://localhost:18635/generate-key'); // Example warm-up request
        console.log('Server warmed up');
    } catch (error) {
        console.error('Error warming up the server:', error.message);
    }
};

// Define endpoints here
// ... [your endpoint definitions here]
// Endpoint to generate a new key
app.post('/generate-key', async (req, res) => {
    try {
        const newKey = uuidv4();
        const storedKeys = await readJsonAsync(storedKeyPath);
        storedKeys[newKey] = 'Nil';
        await writeJsonAsync(storedKeyPath, storedKeys);
        res.json({ success: true, key: newKey });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to update HWID for a given key
app.get('/update-hwid', async (req, res) => {
    const { key, hwid } = req.query;
    try {
        const storedKeys = await readJsonAsync(storedKeyPath);
        if (!storedKeys[key]) return res.status(400).json({ success: false, message: 'Key not found or HWID already set' });
        storedKeys[key] = hwid;
        await writeJsonAsync(storedKeyPath, storedKeys);
        res.json({ success: true, message: 'HWID updated successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to reset HWID for a given key
app.post('/reset-hwid', async (req, res) => {
    const { key } = req.body;
    try {
        const storedKeys = await readJsonAsync(storedKeyPath);
        if (!storedKeys[key]) return res.status(400).json({ success: false, message: 'Key not found' });
        storedKeys[key] = 'Nil';
        await writeJsonAsync(storedKeyPath, storedKeys);
        res.json({ success: true, message: 'HWID reset successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to delete a key
app.post('/delete-key', async (req, res) => {
    const { key } = req.body;
    try {
        const storedKeys = await readJsonAsync(storedKeyPath);
        if (!storedKeys[key]) return res.status(400).json({ success: false, message: 'Key not found' });
        delete storedKeys[key];
        await writeJsonAsync(storedKeyPath, storedKeys);
        res.json({ success: true, message: 'Key deleted successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to fetch all keys and HWIDs as Lua table string
app.get('/fetch-keys-hwids', async (req, res) => {
    try {
        const storedKeys = await readJsonAsync(storedKeyPath);
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
        const storedKeys = await readJsonAsync(storedKeyPath);
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

// Root route to serve an HTML file
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start the server
const startServer = async () => {
    await new Promise((resolve) => {
        app.listen(port, () => {
            console.log(`Worker process listening on http://localhost:${port}`);
            resolve();
        });
    });

    // Warm up the server
    await warmUpServer();
};

if (cluster.isMaster) {
    console.log(`Master ${process.pid} is running`);

    // Fork workers
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }

    cluster.on('exit', (worker, code, signal) => {
        console.log(`Worker ${worker.process.pid} died`);
    });
} else {
    // Workers can share any TCP connection
    // In this case it is an HTTP server
    startServer();
}
