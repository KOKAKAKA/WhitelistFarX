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
exports.handler = async (event, context) => {
    if (event.httpMethod === 'POST') {
        const numberOfKeys = parseInt(event.queryStringParameters.number, 10) || 1;
        try {
            const newKeys = await getKeys(numberOfKeys);
            return {
                statusCode: 200,
                body: JSON.stringify({ keys: newKeys })
            };
        } catch (error) {
            return {
                statusCode: 500,
                body: JSON.stringify({ error: error.message })
            };
        }
    } else {
        return {
            statusCode: 405,
            body: JSON.stringify({ error: 'Method not allowed' })
        };
    }
};
