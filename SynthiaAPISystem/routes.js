const express = require('express');
const bcrypt = require('bcryptjs');
const { queryDatabase } = require('./db');
const { v4: uuidv4 } = require('uuid');
const helmet = require('helmet');
const compression = require('compression');
const { promisify } = require('util');

const router = express.Router();

// Middleware: Security Headers
router.use(helmet());
// Middleware: Compression
router.use(compression());

// Helper: String Validation
const validateString = (str, maxLength) => typeof str === 'string' && str.trim().length > 0 && str.length <= maxLength;

// Helper: Handle Database Query with Error Management
const handleQuery = async (query, params) => {
  try {
    return await queryDatabase(query, params);
  } catch (error) {
    console.error("Database query failed:", error.message);
    throw new Error('Internal server error');
  }
};

// Middleware: User Authentication
const authenticateUser = async (req, res, next) => {
  const { username, password } = req.params;

  if (!validateString(username, 50) || !validateString(password, 255)) {
    return res.status(401).json({ success: false, message: 'Invalid credentials' });
  }

  try {
    const query = `SELECT password FROM users WHERE username = $1;`;
    const result = await handleQuery(query, [username]);

    if (result.length === 0 || !(await bcrypt.compare(password, result[0].password))) {
      return res.status(401).json({ success: false, message: 'Invalid username or password' });
    }

    next();
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
};

// Route: User Signup
router.post('/signup/:username/:password', async (req, res) => {
  const { username, password } = req.params;

  if (!validateString(username, 50) || !validateString(password, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid input' });
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    const newKey = uuidv4();

    await handleQuery(`INSERT INTO users (username, password) VALUES ($1, $2);`, [username, hashedPassword]);
    const result = await handleQuery(`INSERT INTO user_keys (username, key) VALUES ($1, $2) RETURNING key;`, [username, newKey]);

    res.json({ success: true, key: result[0].key });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Route: Generate New Key
router.post('/generate-key/:username/:password', authenticateUser, async (req, res) => {
  const { username } = req.params;

  try {
    const newKey = uuidv4();
    const result = await handleQuery(`INSERT INTO user_keys (username, key) VALUES ($1, $2) RETURNING key;`, [username, newKey]);

    res.json({ success: true, key: result[0].key });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Route: Update HWID
router.get('/update-hwid/:username/:password', authenticateUser, async (req, res) => {
  const { username } = req.params;
  const { key, hwid } = req.query;

  if (!validateString(key, 255) || !validateString(hwid, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid input' });
  }

  try {
    const findQuery = `SELECT hwid FROM user_keys WHERE username = $1 AND key = $2;`;
    const result = await handleQuery(findQuery, [username, key]);

    if (result.length === 0 || result[0].hwid !== 'Nil') {
      return res.status(400).json({ success: false, message: 'Key not found or HWID already set' });
    }

    await handleQuery(`UPDATE user_keys SET hwid = $1 WHERE username = $2 AND key = $3;`, [hwid, username, key]);
    res.json({ success: true, message: 'HWID updated successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Route: Reset HWID
router.post('/reset-hwid/:username/:password', authenticateUser, async (req, res) => {
  const { username } = req.params;
  const { key } = req.body;

  if (!validateString(key, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid key' });
  }

  try {
    const result = await handleQuery(`UPDATE user_keys SET hwid = 'Nil' WHERE username = $1 AND key = $2 RETURNING key;`, [username, key]);

    if (result.rowCount === 0) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }

    res.json({ success: true, message: 'HWID reset successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Route: Delete Key
router.post('/delete-key/:username/:password', authenticateUser, async (req, res) => {
  const { username } = req.params;
  const { key } = req.body;

  if (!validateString(key, 255)) {
    return res.status(400).json({ success: false, message: 'Invalid key' });
  }

  try {
    const result = await handleQuery(`DELETE FROM user_keys WHERE username = $1 AND key = $2;`, [username, key]);

    if (result.rowCount === 0) {
      return res.status(400).json({ success: false, message: 'Key not found' });
    }

    res.json({ success: true, message: 'Key deleted successfully' });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Route: Fetch Keys and HWIDs (Lua Table)
router.get('/fetch-keys-hwids/:username/:password', authenticateUser, async (req, res) => {
  const { username } = req.params;

  try {
    const query = `SELECT key, hwid FROM user_keys WHERE username = $1;`;
    const storedKeys = await handleQuery(query, [username]);

    const luaTableString = "return " + JSON.stringify(
      Object.fromEntries(storedKeys.map(row => [row.key, row.hwid]))
    ).replace(/"(\w+)":/g, '$1:').replace(/"/g, "'");

    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.send(luaTableString);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Route: Fetch Keys and HWIDs (Lua Script) with Optional Key Argument
router.get('/KeyRaw/:username/:password', authenticateUser, async (req, res) => {
  const { username } = req.params;
  const { key } = req.query;

  try {
    const query = key
      ? `SELECT key, hwid FROM user_keys WHERE username = $1 AND key = $2;`
      : `SELECT key, hwid FROM user_keys WHERE username = $1;`;
    const params = key ? [username, key] : [username];
    const storedKeys = await handleQuery(query, params);

    const luaScript = `local KeysAndHwid = {\n${storedKeys.map(row => `    ["${row.key}"] = "${row.hwid}",`).join('\n')}\n}\n\nreturn KeysAndHwid`;

    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    res.type('text/plain');
    res.send(luaScript);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

module.exports = router;
