import React, { useEffect, useState } from 'react';

function KeyDisplay() {
    const [keys, setKeys] = useState({});

    useEffect(() => {
        async function fetchKeys() {
            const response = await fetch('/.netlify/functions/load-keys');
            const result = await response.json();
            setKeys(result);
        }

        fetchKeys();
    }, []);

    return (
        <div>
            <h2>Keys</h2>
            <ul>
                {Object.keys(keys).map(key => (
                    <li key={key}>{key}: {keys[key]}</li>
                ))}
            </ul>
        </div>
    );
}

export default KeyDisplay;
