import React from 'react';
import KeyInput from '../components/KeyInput';
import KeyGenerator from '../components/KeyGenerator';
import DisplayKeys from '../components/DisplayKeys';

const IndexPage = () => (
  <div>
    <h1>Whitelist System</h1>
    <KeyInput />
    <KeyGenerator />
    <DisplayKeys />
  </div>
);

export default IndexPage;
