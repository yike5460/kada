const { expect } = require('chai');
const { initializeSidebar, toggleSidebar } = require('../src/sidebar');

describe('Sidebar functionality', () => {
  it('should toggle sidebar visibility', () => {
    initializeSidebar();
    const sidebar = document.getElementById('video-summarizer-sidebar');
    expect(sidebar.style.display).to.equal('none');
    toggleSidebar(true);
    expect(sidebar.style.display).to.equal('block');
  });
});

// Add more integration tests for your extension's functionality