const fs = require('fs');
const manifest = require('../manifest.json');

const [,, versionType] = process.argv;
const [major, minor, patch] = manifest.version.split('.').map(Number);

switch (versionType) {
  case 'major':
    manifest.version = `${major + 1}.0.0`;
    break;
  case 'minor':
    manifest.version = `${major}.${minor + 1}.0`;
    break;
  case 'patch':
  default:
    manifest.version = `${major}.${minor}.${patch + 1}`;
}

fs.writeFileSync('./manifest.json', JSON.stringify(manifest, null, 2));
console.log(`Version bumped to ${manifest.version}`);