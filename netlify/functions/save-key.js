const { MongoClient } = require('mongodb');

exports.handler = async (event) => {
  const { key, hwid } = JSON.parse(event.body);
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

    const existingEntry = await collection.findOne({ key });
    if (existingEntry) {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: 'Key already exists' }),
      };
    }

    await collection.insertOne({ key, hwid });
    return {
      statusCode: 200,
      body: JSON.stringify({ message: 'Key saved successfully' }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to save key', error: error.message }),
    };
  } finally {
    await client.close();
  }
};
