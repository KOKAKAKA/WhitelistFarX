const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 600 });
const { Pool } = require('pg');
const AsyncLock = require('async-lock');
const Redis = require('ioredis');                          
const redis = new Redis();
const lock = new AsyncLock();
const pool = new Pool({
  user: 'koku',
  host: 'localhost',
  database: 'dtb',
  password: 'password',
  port: 5432,
  max: 50, // Increase pool size
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Utility function to query the database with locking and chunking
async function queryDatabase(query, params = [], cacheKey = null, chunkSize = 0) {
  if (cacheKey) {
    const cachedData = await redis.get(cacheKey);
    if (cachedData) return JSON.parse(cachedData);
  }

  return lock.acquire('dbLock', async () => {
    try {
      const result = await pool.query(query, params);
      
      if (chunkSize > 0) {
        const chunks = [];
        for (let i = 0; i < result.rows.length; i += chunkSize) {
          chunks.push(result.rows.slice(i, i + chunkSize));
        }
        return chunks;
      }
      
      if (cacheKey) {
        await redis.set(cacheKey, JSON.stringify(result.rows), 'EX', 600);
      }
      return result.rows;
    } catch (error) {
      console.error(`Database error: ${error.message}`);
      throw error;
    }
  });
}

module.exports = { queryDatabase };
