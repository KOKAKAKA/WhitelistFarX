import React, { useState } from 'react';
import axios from 'axios';

const generateRandomKey = () => {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  const charactersLength = characters.length;
  for (let i = 0; i < 16; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
};

const KeyGenerator = () => {
  const [key, setKey] = useState('');

  const handleGenerateKey = async () => {
    const newKey = generateRandomKey();
    setKey(newKey);

    try {
      const response = await axios.post('/.netlify/functions/save-key', {
        key: newKey,
        hwid: '' // Assuming HWID is initially empty
      });
      if (response.status === 200) {
        alert('Key saved and copied to clipboard!');
        navigator.clipboard.writeText(newKey);
      } else {
        alert('Failed to save key: ' + response.data.message);
      }
    } catch (error) {
      alert('Error saving key: ' + error.message);
    }
  };

  return (
    <div>
      <button onClick={handleGenerateKey}>Generate Key</button>
      {key && <p>Generated Key: {key}</p>}
    </div>
  );
};

export default KeyGenerator;
