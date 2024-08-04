const { parentPort, workerData } = require('worker_threads');
const fs = require('fs/promises');
const { createClient } = require('redis');

const redisClient = createClient({
  socket: {
    connectTimeout: 10000, // 10 seconds
    readTimeout: 10000, // 10 seconds
  }
});

(async () => {
  try {
    await redisClient.connect();
    const { filePath, data } = workerData;

    // Perform the task
    if (data) {
      await fs.writeFile(filePath, JSON.stringify(data, null, 2));
      await redisClient.set(filePath, JSON.stringify(data));
    } else {
      const fileData = await fs.readFile(filePath, 'utf8');
      const jsonData = JSON.parse(fileData);
      await redisClient.set(filePath, JSON.stringify(jsonData));
      parentPort.postMessage(jsonData);
    }
    parentPort.postMessage('Done');
  } catch (error) {
    parentPort.postMessage(`Error: ${error.message}`);
  } finally {
    await redisClient.quit();
  }
})();
