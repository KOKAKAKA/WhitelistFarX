const { MongoClient } = require('mongodb');
const MONGODB_URI = process.env.MONGODB_URI;
const client = new MongoClient(MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true });

async function loadKeys() {
    try {
        await client.connect();
        const db = client.db('whitelist');
        const collection = db.collection('keys');
        const keys = await collection.find().toArray();
        return keys.reduce((acc, { key, hwid }) => ({ ...acc, [key]: hwid }), {});
    } finally {
        await client.close();
    }
}

module.exports = loadKeys;
