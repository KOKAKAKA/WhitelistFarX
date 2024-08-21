const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 600 });
const { Pool } = require('pg');
const AsyncLock = require('async-lock');

const lock = new AsyncLock();
const pool = new Pool({
  user: 'koku',
  host: 'localhost',
  database: 'dtb',
  password: 'password',
  port: 5432, // Default PostgreSQL port
});

// Utility function to query the database with locking
async function queryDatabase(query, params = [], cacheKey = null) {
  if (cacheKey && cache.has(cacheKey)) {
    return cache.get(cacheKey);
  }

  return lock.acquire('dbLock', async () => {
    try {
      const result = await pool.query(query, params);
      if (cacheKey) {
        cache.set(cacheKey, result.rows);
      }
      return result.rows;
    } catch (error) {
      console.error(`Database error: ${error.message}`);
      throw error;
    }
  });
}

module.exports = { queryDatabase };
