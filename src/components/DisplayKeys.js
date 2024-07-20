import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DisplayKeys = () => {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchKeys = async () => {
      try {
        const response = await axios.get('/.netlify/functions/get-keys');
        setKeys(response.data.keys);
      } catch (error) {
        setError('Failed to load keys.');
      } finally {
        setLoading(false);
      }
    };

    fetchKeys();
  }, []);

  if (loading) return <p>Loading keys...</p>;
  if (error) return <p>{error}</p>;

  return (
    <div>
      <h2>Generated Keys</h2>
      <ul>
        {keys.map((key, index) => (
          <li key={index}>{key.key}</li>
        ))}
      </ul>
    </div>
  );
};

export default DisplayKeys;
