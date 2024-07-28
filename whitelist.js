const express = require('express');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid'); // For generating UUIDs
const { exec } = require('child_process'); // To execute shell scripts
const app = express();
const port = 18635;

// Paths to JSON file
const storedKeyPath = path.join(__dirname, 'StoredKey.json');

// Serve static files from the current directory
app.use(express.static(__dirname));
app.use(express.json()); // To parse JSON bodies

// Function to read JSON data
function readJson(filePath) {
    if (!fs.existsSync(filePath)) {
        return {}; // Return empty object if file doesn't exist
    }
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
}

// Function to write JSON data
function writeJson(filePath, data) {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}


// Endpoint to generate a new key
app.post('/generate-key', (req, res) => {
    try {
        const newKey = uuidv4(); // Generate a new UUID
        const storedKeys = readJson(storedKeyPath);
        storedKeys[newKey] = 'Nil'; // Set HWID to 'Nil'
        writeJson(storedKeyPath, storedKeys);
        res.json({ success: true, key: newKey });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to update HWID for a given key (using GET request)
app.get('/update-hwid', (req, res) => {
    const { key, hwid } = req.query;  // Use query parameters instead of body
    try {
        const storedKeys = readJson(storedKeyPath);
        if (storedKeys[key] === undefined) {
            return res.status(400).json({ success: false, message: 'Key not found' });
        }
        if (storedKeys[key] !== 'Nil') {
            return res.status(400).json({ success: false, message: 'HWID already set' });
        }
        storedKeys[key] = hwid;
        writeJson(storedKeyPath, storedKeys);
        res.json({ success: true, message: 'HWID updated successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to reset HWID for a given key
app.post('/reset-hwid', (req, res) => {
    const { key } = req.body;
    try {
        const storedKeys = readJson(storedKeyPath);
        if (storedKeys[key] === undefined) {
            return res.status(400).json({ success: false, message: 'Key not found' });
        }
        storedKeys[key] = 'Nil';
        writeJson(storedKeyPath, storedKeys);
        res.json({ success: true, message: 'HWID reset successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to fetch all keys and HWIDs, return as Lua table string
app.get('/fetch-keys-hwids', (req, res) => {
    try {
        const storedKeys = readJson(storedKeyPath);
        let luaTableString = "return " + JSON.stringify(storedKeys).replace(/"(\w+)":/g, '$1:').replace(/"/g, "'");
        res.setHeader('Cache-Control', 'no-store');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
        res.send(luaTableString);
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// New endpoint to fetch keys and HWIDs as a Lua script
app.get('/KeyRaw', (req, res) => {
    try {
        const storedKeys = readJson(storedKeyPath);
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
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
