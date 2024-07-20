const { MongoClient } = require('mongodb');

exports.handler = async () => {
  const uri = process.env.MONGODB_URI;

  if (!uri) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Missing MongoDB connection string' }),
    };
  }

  const client = new MongoClient(uri, { useNewUrlParser: true, useUnifiedTopology: true });

  try {
    await client.connect();
    const database = client.db('whitelist');
    const collection = database.collection('keys');

    const keys = await collection.find({}).toArray();
    return {
      statusCode: 200,
      body: JSON.stringify({ keys }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to fetch keys', error: error.message }),
    };
  } finally {
    await client.close();
  }
};
