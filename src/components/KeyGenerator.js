// KeyGenerator.js

import React from 'react';

function KeyGenerator() {
    const handleClick = async () => {
        try {
            const response = await fetch('/.netlify/functions/get-keys?number=1', { method: 'POST' });
            const result = await response.json();
            console.log(result); // Log result
            // Handle result (e.g., display key, update state)
        } catch (error) {
            console.error('Error fetching keys:', error); // Log errors
        }
    };

    return (
        <button onClick={handleClick}>Generate Key</button>
    );
}

export default KeyGenerator;
