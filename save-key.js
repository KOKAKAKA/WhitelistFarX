const fetch = require('node-fetch');

exports.handler = async (event) => {
  const { key } = JSON.parse(event.body);

  // Replace with your backend API URL or logic to handle the key
  const apiUrl = 'https://whitelistsynthia.netlify.app/api/save-key';

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
    });

    const result = await response.json();

    return {
      statusCode: 200,
      body: JSON.stringify({ message: result.message }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ message: 'Failed to save key' }),
    };
  }
};
