const express = require('express');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 18635;

app.use(express.json());
app.use(express.static(__dirname)); // Serve static files from the current directory

// Path to whitelist.json
const whitelistPath = path.join(__dirname, 'whitelist.json');

// Function to read whitelist.json
function readWhitelist() {
    const data = fs.readFileSync(whitelistPath, 'utf8');
    return JSON.parse(data);
}

// Function to write to whitelist.json
function writeWhitelist(data) {
    fs.writeFileSync(whitelistPath, JSON.stringify(data, null, 2), 'utf8');
}

// Serve index.html at the root
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Endpoint to get the whitelist
app.get('/whitelist', (req, res) => {
    const whitelist = readWhitelist();
    res.json(whitelist);
});

// Endpoint to update a key with HWID
app.post('/update-key', (req, res) => {
    const { key, hwid } = req.body;
    const whitelist = readWhitelist();
    
    if (whitelist[key]) {
        whitelist[key].Hwid = hwid;
        writeWhitelist(whitelist);
        res.json({ success: true, key: whitelist[key] });
    } else {
        res.status(404).send('Key not found');
    }
});

// Endpoint to generate a new key
app.post('/generate-key', (req, res) => {
    const whitelist = readWhitelist();
    const newKey = uuidv4();
    whitelist[newKey] = { Key: newKey, Hwid: "Nil" };
    writeWhitelist(whitelist);
    res.json({ success: true, key: newKey });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
