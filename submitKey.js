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

  const { key, hwid } = JSON.parse(event.body);

  if (!key || !hwid) {
    return {
      statusCode: 400,
      body: JSON.stringify({ message: 'Missing key or HWID' }),
    };
  }

  if (whitelist[key]) {
    if (whitelist[key].includes(hwid)) {
      return {
        statusCode: 200,
        body: JSON.stringify({ message: 'HWID already whitelisted' }),
      };
    }

    whitelist[key].push(hwid);
  } else {
    whitelist[key] = [hwid];
  }

  fs.writeFileSync(path, JSON.stringify(whitelist, null, 2));

  return {
    statusCode: 200,
    body: JSON.stringify({ message: 'HWID added to whitelist' }),
  };
};
