aconst fs = require('fs');
const path = require('path');

const whitelistFile = path.join(__dirname, 'whitelist.json');

function updateWhitelist(key, hwid) {
    const data = JSON.parse(fs.readFileSync(whitelistFile, 'utf8'));

    if (!data[key]) {
        return { success: false, message: 'Invalid key' };
    }

    if (data[key].includes(hwid)) {
        return { success: false, message: 'HWID already associated with this key' };
    }

    data[key].push(hwid);
    fs.writeFileSync(whitelistFile, JSON.stringify(data, null, 2));
    return { success: true, message: 'HWID added successfully' };
}

const key = process.argv[2];
const hwid = process.argv[3];
if (!key || !hwid) {
    console.error('Key and HWID are required');
    process.exit(1);
}

const result = updateWhitelist(key, hwid);
console.log(result.message);
