import React, { useState } from 'react';
import axios from 'axios';

const KeyInput = () => {
  const [key, setKey] = useState('');
  const [message, setMessage] = useState('');

  const handleInputChange = (e) => setKey(e.target.value);

  const handleSaveKey = async () => {
    try {
      const response = await axios.post('/.netlify/functions/save-key', { key, hwid: 'sample-hwid' });
      setMessage(response.data.message);
    } catch (error) {
      setMessage('Error saving key.');
    }
  };

  return (
    <div>
      <input 
        type="text" 
        value={key} 
        onChange={handleInputChange} 
        placeholder="Enter your key" 
        required 
      />
      <button onClick={handleSaveKey}>Save Key</button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default KeyInput;
