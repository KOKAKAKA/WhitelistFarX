const { exec } = require('child_process');

// Script to restart the server
exec('node whitelist.js', (error, stdout, stderr) => {
  if (error) {
    console.error(`Error restarting server: ${error.message}`);
    return;
  }
  if (stderr) {
    console.error(`Restart stderr: ${stderr}`);
    return;
  }
  console.log(`Restart stdout: ${stdout}`);
});
