const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 600 });
const { Pool } = require('pg');
const AsyncLock = require('async-lock');
const Redis = require('ioredis');
const zlib = require('zlib'); // Add compression
const { pipeline } = require('stream');
const redis = new Redis();
const lock = new AsyncLock();

const pool = new Pool({
  user: 'koku',
  host: 'localhost',
  database: 'dtb',
  password: 'password',
  port: 5432,
  max: 50, // Increased pool size
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Utility function to compress data
function compressData(data) {
  return new Promise((resolve, reject) => {
    zlib.gzip(data, (err, buffer) => {
      if (err) reject(err);
      else resolve(buffer);
    });
  });
}

// Utility function to decompress data
function decompressData(data) {
  return new Promise((resolve, reject) => {
    zlib.gunzip(data, (err, buffer) => {
      if (err) reject(err);
      else resolve(buffer.toString());
    });
  });
}

// Utility function to query the database with locking, chunking, and compression
async function queryDatabase(query, params = [], cacheKey = null, chunkSize = 0) {
  if (cacheKey) {
    const cachedData = await redis.getBuffer(cacheKey); // Use getBuffer to handle binary data
    if (cachedData) {
      const decompressedData = await decompressData(cachedData);
      return JSON.parse(decompressedData);
    }
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
        const compressedData = await compressData(JSON.stringify(result.rows));
        await redis.set(cacheKey, compressedData, 'EX', 600);
      }

      return result.rows;
    } catch (error) {
      console.error(`Database error: ${error.message}`);
      throw error;
    }
  });
}

// Stream large query results in chunks
async function queryDatabaseStream(query, params = [], onChunk, chunkSize = 100) {
  const client = await pool.connect();

  try {
    const queryStream = client.query(new Cursor(query, params));

    const readNextChunk = () => {
      queryStream.read(chunkSize, async (err, rows) => {
        if (err) throw err;

        if (rows.length > 0) {
          await onChunk(rows);
          readNextChunk(); // Fetch the next chunk
        } else {
          queryStream.close(() => client.release()); // Release the client when done
        }
      });
    };

    readNextChunk();
  } catch (error) {
    console.error(`Database stream error: ${error.message}`);
    client.release();
    throw error;
  }
}

module.exports = { queryDatabase, queryDatabaseStream };
