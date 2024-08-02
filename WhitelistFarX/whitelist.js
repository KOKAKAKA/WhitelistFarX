const express = require('express');
const fs = require('fs/promises'); // Use promises for async file I/O
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 18635;

const storedKeyPath = path.join(__dirname, 'StoredKey.json');

app.use(express.json());

async function readJson(filePath) {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading file: ${error}`);
    return {};
  }
}

async function writeJson(filePath, data) {
  try {
    await fs.writeFile(filePath, JSON.stringify(data, null, 2));
  } catch (error) {
    console.error(`Error writing file: ${error}`);
  }
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

// Endpoint to update HWID for a given key
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

        // Reset HWID for the key
        storedKeys[key] = 'Nil';
        writeJson(storedKeyPath, storedKeys);

        res.json({ success: true, message: 'HWID reset successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
});

// Endpoint to delete a key
app.post('/delete-key', (req, res) => {
    const { key } = req.body;
    try {
        const storedKeys = readJson(storedKeyPath);
        if (storedKeys[key] === undefined) {
            return res.status(400).json({ success: false, message: 'Key not found' });
        }
        delete storedKeys[key];
        writeJson(storedKeyPath, storedKeys);
        res.json({ success: true, message: 'Key deleted successfully' });
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

// Start the server
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
