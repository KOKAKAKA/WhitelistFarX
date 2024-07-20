// netlify/functions/get-keys.js

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
    return newKeys; // Return the new keys
}

// API handler
module.exports = async (req, res) => {
    if (req.method === 'POST') {
        const numberOfKeys = parseInt(req.query.number, 10) || 1;
        try {
            console.log(`Generating ${numberOfKeys} keys`); // Log number of keys
            const newKeys = await getKeys(numberOfKeys);
            console.log('Generated keys:', newKeys); // Log generated keys
            res.status(200).json({ keys: newKeys });
        } catch (error) {
            console.error('Error generating keys:', error); // Log errors
            res.status(500).json({ error: error.message });
        }
    } else {
        res.status(405).json({ error: 'Method not allowed' });
    }
};
