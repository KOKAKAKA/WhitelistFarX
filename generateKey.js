const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const whitelistFile = path.join(__dirname, 'whitelist.json');

function generateRandomKey(length = 16) {
    return crypto.randomBytes(length).toString('hex');
}

function addKeyToWhitelist(key) {
    const data = JSON.parse(fs.readFileSync(whitelistFile, 'utf8'));

    if (data[key]) {
        console.log('Key already exists.');
        return;
    }

    data[key] = [];
    fs.writeFileSync(whitelistFile, JSON.stringify(data, null, 2));
    console.log(`Key ${key} added to whitelist.`);
}

const newKey = generateRandomKey();
addKeyToWhitelist(newKey);
console.log(`Generated key: ${newKey}`);
