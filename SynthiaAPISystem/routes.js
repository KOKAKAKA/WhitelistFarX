const express = require('express');
const bcrypt = require('bcryptjs');
const { queryDatabase } = require('./db');
const { v4: uuidv4 } = require('uuid');
const rateLimit = require('express-rate-limit'); // Rate limiting library
const helmet = require('helmet'); // Security headers library

const router = express.Router();

// Middleware to apply security headers
router.use(helmet());

// Rate limiter to prevent brute force attacks
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: "Too many requests from this IP, please try again later."
});
router.use(apiLimiter);

// Middleware to validate user and password
const authenticateUser = async (req, res, next) => {
  const { username, password } = req.query;

  if (!username || !password) return res.status(401).json({ success: false, message: 'Username and password required' });

  try {
    const query = `SELECT password FROM users WHERE username = $1;`;
    const result = await queryDatabase(query, [username]);

    if (result.length === 0) return res.status(401).json({ success: false, message: 'Invalid username or password' });

    const hashedPassword = result[0].password;
    const isMatch = await bcrypt.compare(password, hashedPassword);

    if (!isMatch) return res.status(401).json({ success: false, message: 'Invalid username or password' });

    next();
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};

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

// Middleware to validate user and password for other endpoints
const validateUserAndPassword = async (req, res, next) => {
  const { username, password } = req.params;

  if (!username || !password) return res.status(401).json({ success: false, message: 'Username and password required' });

  try {
    const query = `SELECT password FROM users WHERE username = $1;`;
    const result = await queryDatabase(query, [username]);

    if (result.length === 0) return res.status(401).json({ success: false, message: 'Invalid username or password' });

    const hashedPassword = result[0].password;
    const isMatch = await bcrypt.compare(password, hashedPassword);

    if (!isMatch) return res.status(401).json({ success: false, message: 'Invalid username or password' });

    next();
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};

// Helper function to validate strings
const validateString = (str, maxLength) => {
  return typeof str === 'string' && str.length <= maxLength;
};

// Generate a new key for a specific user
router.post('/generate-key/:username/:password', validateUserAndPassword, async (req, res) => {
  const { username } = req.params;
  try {
    const newKey = uuidv4();
    const query = `
      INSERT INTO user_keys (username, key) 
      VALUES ($1, $2) 
      RETURNING key;
    `;
    const result = await queryDatabase(query, [username, newKey]);
    res.json({ success: true, key: result[0].key });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Update HWID for a specific user and key
router.get('/update-hwid/:username/:password', validateUserAndPassword, async (req, res) => {
  const { username } = req.params;
  const { key, hwid } = req.query;

  // Validate HWID
  if (!validateString(hwid, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid HWID' });
  }

  try {
    const findQuery = `SELECT hwid FROM user_keys WHERE username = $1 AND key = $2;`;
    const result = await queryDatabase(findQuery, [username, key]);

    if (result.length === 0) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }

    if (result[0].hwid !== 'Nil') {
      return res.status(400).json({ success: false, message: 'HWID already set' });
    }

    const updateQuery = `
      UPDATE user_keys 
      SET hwid = $1 
      WHERE username = $2 AND key = $3;
    `;
    await queryDatabase(updateQuery, [hwid, username, key]);
    res.json({ success: true, message: 'HWID updated successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Reset HWID for a given user and key
router.post('/reset-hwid/:username/:password', validateUserAndPassword, async (req, res) => {
  const { username } = req.params;
  const { key } = req.body;

  // Validate key
  if (!validateString(key, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid key' });
  }

  try {
    const updateQuery = `
      UPDATE user_keys 
      SET hwid = 'Nil' 
      WHERE username = $1 AND key = $2;
    `;
    const result = await queryDatabase(updateQuery, [username, key]);

    if (result.rowCount === 0) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }

    res.json({ success: true, message: 'HWID reset successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Delete a key for a specific user
router.post('/delete-key/:username/:password', validateUserAndPassword, async (req, res) => {
  const { username } = req.params;
  const { key } = req.body;

  // Validate key
  if (!validateString(key, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid key' });
  }

  try {
    const deleteQuery = `
      DELETE FROM user_keys 
      WHERE username = $1 AND key = $2;
    `;
    const result = await queryDatabase(deleteQuery, [username, key]);

    if (result.rowCount === 0) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }

    res.json({ success: true, message: 'Key deleted successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Fetch all keys and HWIDs for a specific user as a Lua table string
router.get('/fetch-keys-hwids/:username/:password', validateUserAndPassword, async (req, res) => {
  const { username } = req.params;
  try {
    const query = `
      SELECT key, hwid 
      FROM user_keys 
      WHERE username = $1;
    `;
    const storedKeys = await queryDatabase(query, [username]);

    const keyObject = {};
    storedKeys.forEach(row => {
      keyObject[row.key] = row.hwid;
    });

    const luaTableString = "return " + JSON.stringify(keyObject).replace(/"(\w+)":/g, '$1:').replace(/"/g, "'");
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(luaTableString);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Fetch keys and HWIDs as a Lua script for a specific user
router.get('/KeyRaw/:username/:password', validateUserAndPassword, async (req, res) => {
  const { username } = req.params;
  try {
    const query = `
      SELECT key, hwid 
      FROM user_keys 
      WHERE username = $1;
    `;
    const storedKeys = await queryDatabase(query, [username]);

    let luaTableString = "local KeysAndHwid = {\n";
    storedKeys.forEach(row => {
      luaTableString += `    ["${row.key}"] = "${row.hwid}",\n`;
    });
    luaTableString += "}\n\nreturn KeysAndHwid";
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.type('text/plain');
    res.send(luaTableString);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

module.exports = router;
