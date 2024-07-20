const { MongoClient } = require('mongodb');
const MONGODB_URI = process.env.MONGODB_URI;
const client = new MongoClient(MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true });

async function validateKey(key) {
    try {
        await client.connect();
        const db = client.db('whitelist');
        const collection = db.collection('keys');
        const result = await collection.findOne({ key });
        return result ? result.hwid : null;
    } finally {
        await client.close();
    }
}

module.exports = validateKey;

// API handler
exports.handler = async (event, context) => {
    if (event.httpMethod === 'POST') {
        const { key } = JSON.parse(event.body);
        try {
            const hwid = await validateKey(key);
            return {
                statusCode: 200,
                body: JSON.stringify({ hwid })
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
