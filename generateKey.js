const crypto = require('crypto');
const fs = require('fs');
const path = './whitelist.json';
let whitelist;

try {
  whitelist = require(path);
} catch (e) {
  whitelist = {}; // Initialize if file doesn't exist
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ message: 'Method not allowed' }),
    };
  }

  const key = crypto.randomBytes(16).toString('hex'); // Generate a random 32-character hexadecimal key

  whitelist[key] = []; // Initialize the key with an empty array

  fs.writeFileSync(path, JSON.stringify(whitelist, null, 2));

  return {
    statusCode: 200,
    body: JSON.stringify({ message: `Key generated: ${key}` }),
  };
};
