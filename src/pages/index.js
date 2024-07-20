import React from 'react';
// In src/pages/YourPage.js or similar
import KeyGenerator from '../components/KeyGenerator';
import KeyDisplay from '../components/KeyDisplay';
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
