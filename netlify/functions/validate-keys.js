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
