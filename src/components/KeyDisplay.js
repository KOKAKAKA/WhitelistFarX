import React, { useEffect, useState } from 'react';

function KeyDisplay() {
    const [key, setKey] = useState('');

    useEffect(() => {
        async function fetchKey() {
            const response = await fetch('/api/get-key');
            const result = await response.json();
            setKey(result.key);
        }

        fetchKey();
    }, []);

    return <div>Your Key: {key}</div>;
}

export default KeyDisplay;
