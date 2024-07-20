const fs = require('fs');
const path = require('path');

exports.handler = async (event) => {
  const { key, hwid } = JSON.parse(event.body);
  const whitelistPath = path.resolve(__dirname, '../whitelist.json');

  let whitelist;
  try {
    const data = fs.readFileSync(whitelistPath);
    whitelist = JSON.parse(data);
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to read whitelist' }),
    };
  }

  const existingEntry = whitelist.keys.find(entry => entry.key === key);
  if (existingEntry) {
    return {
      statusCode: 400,
      body: JSON.stringify({ message: 'Key already exists' }),
    };
  }

  whitelist.keys.push({ key, hwid });

  try {
    fs.writeFileSync(whitelistPath, JSON.stringify(whitelist, null, 2));
    return {
      statusCode: 200,
      body: JSON.stringify({ message: 'Whitelist updated successfully' }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to update whitelist' }),
    };
  }
};
