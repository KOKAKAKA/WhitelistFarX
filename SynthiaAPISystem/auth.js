const express = require('express');
const bcrypt = require('bcryptjs');
const { queryDatabase } = require('./db');
const { v4: uuidv4 } = require('uuid');
const router = express.Router();

// Signup route
router.post('/signup/:username/:password', async (req, res) => {
  const { username, password } = req.params;

  if (!username || !password) {
    return res.status(400).json({ success: false, message: 'Username and password required' });
  }

  try {
    // Hash the password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Generate an initial key
    const newKey = uuidv4();

    // Save user and initial key in the database
    const insertUserQuery = `
      INSERT INTO users (username, password) 
      VALUES ($1, $2) 
      RETURNING username;
    `;
    const insertKeyQuery = `
      INSERT INTO user_keys (username, key) 
      VALUES ($1, $2) 
      RETURNING key;
    `;

    await queryDatabase(insertUserQuery, [username, hashedPassword]);
    const result = await queryDatabase(insertKeyQuery, [username, newKey]);

    res.json({ success: true, key: result[0].key });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

module.exports = router;
