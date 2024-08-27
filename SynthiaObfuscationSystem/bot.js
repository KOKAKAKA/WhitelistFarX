const { Client, GatewayIntentBits, ApplicationCommandOptionType } = require('discord.js');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Load the bot token
const tokenPath = path.join(__dirname, 'SavedToken.json');
let token;
try {
  token = JSON.parse(fs.readFileSync(tokenPath, 'utf8')).token;
} catch (error) {
  console.error('Failed to load token:', error);
  process.exit(1); // Exit if token loading fails
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

const SERVER_ID = '1253670424345051146';
const CHANNEL_ID = '1253670424785453126';

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}!`);

  // Register the /key command
  try {
    // Check if the command already exists before creating
    const commands = await client.application.commands.fetch();
    if (!commands.some(cmd => cmd.name === 'key')) {
      await client.application.commands.create({
        name: 'key',
        description: 'Generate and update a key with the specified HWID.',
        options: [{
          name: 'hwid',
          type: ApplicationCommandOptionType.String,
          description: 'The HWID to associate with the generated key.',
          required: true
        }]
      }, SERVER_ID);
      console.log('Successfully registered the /key command.');
    }
  } catch (error) {
    console.error('Error registering commands:', error);
  }
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isCommand()) return;

  const { commandName, channelId, guildId, options } = interaction;

  // Restrict to specific server and channel
  if (guildId !== SERVER_ID || channelId !== CHANNEL_ID) {
    return interaction.reply({ content: 'This command is not available here.', ephemeral: true });
  }

  if (commandName === 'key') {
    const hwid = options.getString('hwid');

    // Ephemeral response while processing
    await interaction.reply({ content: 'Processing Key...', ephemeral: true });

    try {
      // Generate key with retries
      const generateKeyResponse = await retryRequest(
        () => axios.post('http://localhost:18635/generate-key'),
        5,
        2000
      );
      const { key } = generateKeyResponse.data;

      // Update HWID with retries
      await retryRequest(
        () => axios.get(`http://localhost:18635/update-hwid?key=${key}&hwid=${hwid}`),
        5,
        2000
      );

      // Success message
      await interaction.editReply({ content: `Success! Key: ${key}`, ephemeral: true });
    } catch (error) {
      console.error('Error processing the request:', error);
      await interaction.editReply({ content: 'Error processing the request.', ephemeral: true });
    }
  }
});

// Helper function for retrying requests
async function retryRequest(requestFunc, maxRetries, delay) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFunc();
    } catch (error) {
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw error;
      }
    }
  }
}

// Log in to Discord
client.login(token);
