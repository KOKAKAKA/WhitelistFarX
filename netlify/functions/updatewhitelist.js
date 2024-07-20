const fs = require('fs');
const path = require('path');

exports.handler = async (event) => {
  console.log('Received event:', JSON.stringify(event, null, 2)); // Log the event data

  const { key, hwid } = JSON.parse(event.body);

  const whitelistPath = path.resolve(__dirname, '../whitelist.json');

  let whitelist;
  try {
    const data = fs.readFileSync(whitelistPath);
    whitelist = JSON.parse(data);
  } catch (error) {
    console.error('Failed to read whitelist:', error); // Log error
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to read whitelist' }),
    };
  }

  const existingEntry = whitelist.keys.find(entry => entry.hwid === hwid);
  if (existingEntry) {
    return {
      statusCode: 400,
      body: JSON.stringify({ message: 'HWID already exists' }),
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
    console.error('Failed to update whitelist:', error); // Log error
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to update whitelist' }),
    };
  }
};
