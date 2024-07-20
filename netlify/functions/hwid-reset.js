const fs = require('fs');
const path = require('path');

exports.handler = async (event) => {
  const { key } = JSON.parse(event.body);
  const whitelistPath = path.resolve(__dirname, '../whitelist.json');

  try {
    const data = fs.readFileSync(whitelistPath);
    let whitelist = JSON.parse(data);

    // Find the key entry
    const entry = whitelist.keys.find(entry => entry.key === key);

    if (entry) {
      // Reset HWID
      entry.hwid = "";
      
      // Write changes back to file
      fs.writeFileSync(whitelistPath, JSON.stringify(whitelist, null, 2));
      
      return {
        statusCode: 200,
        body: JSON.stringify({ message: 'HWID reset successfully' }),
      };
    } else {
      return {
        statusCode: 404,
        body: JSON.stringify({ message: 'Key not found' }),
      };
    }
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to read or update whitelist' }),
    };
  }
};
