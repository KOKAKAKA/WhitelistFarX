import React, { useState } from 'react';

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

  const handleGenerateKey = () => {
    const newKey = generateRandomKey();
    setKey(newKey);
    navigator.clipboard.writeText(newKey).then(
      () => alert('Key copied to clipboard!'),
      (err) => alert('Failed to copy key: ' + err)
    );
  };

  return (
    <div>
      <button onClick={handleGenerateKey}>Generate Key</button>
      {key && <p>Generated Key: {key}</p>}
    </div>
  );
};

export default KeyGenerator;
