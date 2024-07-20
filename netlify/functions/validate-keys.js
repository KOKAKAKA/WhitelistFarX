const fs = require('fs');
const path = require('path');

exports.handler = async (event) => {
  const { key, hwid } = JSON.parse(event.body);
  const whitelistPath = path.resolve(__dirname, '../whitelist.json');

  try {
    const data = fs.readFileSync(whitelistPath);
    const whitelist = JSON.parse(data);

    const validEntry = whitelist.keys.find(entry => entry.key === key && entry.hwid === hwid);

    if (validEntry) {
      return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Key and HWID are valid' }),
      };
    } else {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: 'Invalid key or HWID' }),
      };
    }
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to read whitelist' }),
    };
  }
};
