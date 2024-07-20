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
            const newKeys = await getKeys(numberOfKeys);
            res.status(200).json({ keys: newKeys });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    } else {
        res.status(405).json({ error: 'Method not allowed' });
    }
};
