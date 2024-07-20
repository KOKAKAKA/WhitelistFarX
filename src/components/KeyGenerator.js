import React from 'react';

function KeyGenerator() {
    const handleClick = async () => {
        const response = await fetch('/api/get-keys?number=1', { method: 'POST' });
        const result = await response.json();
        console.log(result); // Handle result
    };

    return (
        <button onClick={handleClick}>Generate Key</button>
    );
}

export default KeyGenerator;
