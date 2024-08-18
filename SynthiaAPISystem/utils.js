const { exec } = require('child_process');
const process = require('process');
const os = require('os');
const NodeCache = require('node-cache');

const cache = new NodeCache({ stdTTL: 60, checkperiod: 120 });

let serverReady = false;

function isServerReady() {
  return serverReady;
}

function setServerReady(status) {
  serverReady = status;
}

async function initializeServer() {
  try {
    setServerReady(true);
    console.log('Server is fully initialized and ready to handle requests.');
  } catch (error) {
    console.error(`Error during server initialization: ${error.message}`);
  }
}

function restartServer() {
  console.log('Restarting server.');
  setTimeout(() => {
    exec(`node restart.js`, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error executing restart script: ${error.message}`);
        return;
      }
      if (stderr) {
        console.error(`Restart script stderr: ${stderr}`);
      }
      console.log(`Restart script stdout: ${stdout}`);
    });
    process.exit();
  }, 1000); // 1-second delay
}

function clearCache() {
  console.log('Clearing cache');
  cache.flushAll();
}

function monitorServer() {
  setInterval(async () => {
    const freeMemory = os.freemem();
    const totalMemory = os.totalmem();
    const memoryUsage = ((totalMemory - freeMemory) / totalMemory) * 100;

    if (memoryUsage > 80) {
      console.log('High memory usage detected, clearing cache.');
      clearCache();
    }

    if (process.uptime() > 24 * 60 * 60) {
      console.log('Uptime exceeded 24 hours, restarting server.');
      restartServer();
    }
  }, 5 * 60 * 1000); // Every 10 minutes
}

module.exports = { initializeServer, restartServer, clearCache, monitorServer, isServerReady };
