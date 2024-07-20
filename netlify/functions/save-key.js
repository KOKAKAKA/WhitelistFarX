// netlify/functions/save-key.js
const { MongoClient } = require('mongodb');

// Replace this with your actual MongoDB connection string
const uri = process.env.MONGODB_URI;

exports.handler = async function(event) {
  if (event.httpMethod === 'POST') {
    try {
      const client = new MongoClient(uri, { useNewUrlParser: true, useUnifiedTopology: true });
      await client.connect();

      const data = JSON.parse(event.body);

      // Replace 'yourDatabase' and 'yourCollection' with your actual DB and collection names
      const db = client.db('yourDatabase');
      const collection = db.collection('yourCollection');

      await collection.insertOne(data);

      await client.close();

      return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Data saved successfully' })
      };
    } catch (error) {
      console.error('Error saving data:', error);
      return {
        statusCode: 500,
        body: JSON.stringify({ error: 'Failed to save data' })
      };
    }
  }

  return {
    statusCode: 405,
    body: JSON.stringify({ error: 'Method not allowed' })
  };
};
