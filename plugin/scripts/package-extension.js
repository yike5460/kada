const fs = require('fs');
const archiver = require('archiver');

const output = fs.createWriteStream('extension.zip');
const archive = archiver('zip', { zlib: { level: 9 } });

output.on('close', () => {
  console.log('Extension packaged successfully');
});

archive.on('error', (err) => {
  throw err;
});

archive.pipe(output);
archive.directory('src/', 'src');
archive.file('manifest.json', { name: 'manifest.json' });
archive.finalize();