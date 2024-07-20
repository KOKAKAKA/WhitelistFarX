const fs = require('fs');
const path = require('path');

exports.handler = async () => {
  const whitelistPath = path.resolve(__dirname, '../whitelist.json');

  try {
    const data = fs.readFileSync(whitelistPath);
    const whitelist = JSON.parse(data);
    return {
      statusCode: 200,
      body: JSON.stringify({ keys: whitelist.keys }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to read whitelist' }),
    };
  }
};
