const crypto = require('crypto');
const saveKey = require('./save-key');
const updateWhitelist = require('./updatewhitelist');

function generateKey() {
    return crypto.randomBytes(16).toString('hex');
}

async function getKeys(numberOfKeys) {
    const newKeys = {};
    for (let i = 0; i < numberOfKeys; i++) {
        const key = generateKey();
        const hwid = '';
        await saveKey(key, hwid);
        newKeys[key] = hwid;
    }
    await updateWhitelist(newKeys);
}

module.exports = getKeys;
