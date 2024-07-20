import React from 'react';
import KeyGenerator from './KeyGenerator';
import KeyDisplay from './KeyDisplay';

function IndexPage() {
    return (
        <div>
            <h1>Whitelist Management</h1>
            <KeyGenerator />
            <KeyDisplay />
        </div>
    );
}

export default IndexPage;
