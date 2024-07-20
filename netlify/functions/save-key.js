const fs = require('fs');
const path = require('path');

exports.handler = async (event) => {
  const { key, hwid } = JSON.parse(event.body);
  const whitelistPath = path.resolve(__dirname, '../whitelist.json');

  try {
    const data = fs.readFileSync(whitelistPath, 'utf-8');
    const whitelist = JSON.parse(data);

    // Check if key already exists
    if (whitelist.keys.find(entry => entry.key === key)) {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: 'Key already exists' }),
      };
    }

    // Add the new key
    whitelist.keys.push({ key, hwid });

    // Write updated whitelist back to the file
    fs.writeFileSync(whitelistPath, JSON.stringify(whitelist, null, 2));

    return {
      statusCode: 200,
      body: JSON.stringify({ message: 'Key saved successfully' }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to save key' }),
    };
  }
};
