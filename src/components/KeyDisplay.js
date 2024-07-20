import React, { useEffect, useState } from 'react';
import axios from 'axios';

const KeyDisplay = () => {
  const [keys, setKeys] = useState([]);

  useEffect(() => {
    axios.get('/.netlify/functions/get-keys')
      .then(response => {
        setKeys(response.data.keys);
      })
      .catch(error => {
        console.error("Error fetching keys:", error);
      });
  }, []);

  return (
    <div>
      <h2>Key List</h2>
      <ul>
        {keys.map((entry, index) => (
          <li key={index}>
            {entry.key} - {entry.hwid}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default KeyDisplay;
