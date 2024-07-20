const fetch = require('node-fetch');

exports.handler = async (event) => {
  const { key, hwid } = JSON.parse(event.body);

  const apiUrl = 'https://whitelistsynthia.netlify.app/.netlify/functions/updatewhitelist';

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, hwid }),
    });

    const result = await response.json();
    return {
      statusCode: response.status,
      body: JSON.stringify(result),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to save key and HWID' }),
    };
  }
};
