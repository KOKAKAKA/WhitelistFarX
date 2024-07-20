const { MongoClient } = require('mongodb');
const MONGODB_URI = process.env.MONGODB_URI;
const client = new MongoClient(MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true });

async function resetHWID(key) {
    try {
        await client.connect();
        const db = client.db('whitelist');
        const collection = db.collection('keys');
        await collection.updateOne(
            { key },
            { $set: { hwid: '' } }
        );
    } finally {
        await client.close();
    }
}

module.exports = resetHWID;

// API handler
exports.handler = async (event, context) => {
    if (event.httpMethod === 'POST') {
        const { key } = JSON.parse(event.body);
        try {
            await resetHWID(key);
            return {
                statusCode: 200,
                body: JSON.stringify({ message: 'HWID reset successfully' })
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
