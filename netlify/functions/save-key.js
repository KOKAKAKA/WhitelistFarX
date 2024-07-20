const { MongoClient } = require('mongodb');
const MONGODB_URI = process.env.MONGODB_URI;
const client = new MongoClient(MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true });

async function saveKey(key, hwid) {
    try {
        await client.connect();
        const db = client.db('whitelist');
        const collection = db.collection('keys');
        await collection.updateOne(
            { key },
            { $set: { hwid } },
            { upsert: true }
        );
    } finally {
        await client.close();
    }
}

module.exports = saveKey;
