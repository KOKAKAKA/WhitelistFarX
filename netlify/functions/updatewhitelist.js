const { Octokit } = require('@octokit/rest');
const PAT = process.env.PAT;
const octokit = new Octokit({ auth: PAT });

async function updateWhitelist(keys) {
    const repo = 'KOKAKAKA/WhitelistFarX';
    const filePath = 'whitelist.json';

    // Get the current file content
    const { data: { content, sha } } = await octokit.repos.getContent({
        owner: 'KOKAKAKA',
        repo,
        path: filePath
    });

    // Decode content
    const fileContent = Buffer.from(content, 'base64').toString('utf8');
    const whitelist = JSON.parse(fileContent);

    // Update whitelist with new keys
    Object.assign(whitelist, keys);

    // Update file on GitHub
    await octokit.repos.createOrUpdateFileContents({
        owner: 'KOKAKAKA',
        repo,
        path: filePath,
        message: 'Update whitelist.json',
        content: Buffer.from(JSON.stringify(whitelist, null, 2)).toString('base64'),
        sha
    });
}

module.exports = updateWhitelist;
