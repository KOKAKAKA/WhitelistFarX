import React from 'react';

function KeyGenerator() {
    const handleClick = async () => {
        const response = await fetch('/.netlify/functions/get-keys?number=1', { method: 'POST' });
        const result = await response.json();
        console.log(result); // Log the result to verify key generation
    };

    return (
        <button onClick={handleClick}>Generate Key</button>
    );
}

export default KeyGenerator;
