const puppeteer = require('puppeteer');

describe('Extension E2E Tests', () => {
  let browser;
  let page;

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: false,
      args: [
        `--disable-extensions-except=${PATH_TO_EXTENSION}`,
        `--load-extension=${PATH_TO_EXTENSION}`
      ]
    });
    page = await browser.newPage();
  });

  test('Extension icon appears on YouTube', async () => {
    await page.goto('https://www.youtube.com');
    const extensionIcon = await page.$('.video-summarizer-icon');
    expect(extensionIcon).not.toBeNull();
  });

  test('Sidebar appears when icon is clicked', async () => {
    await page.click('.video-summarizer-icon');
    const sidebar = await page.$('#video-summarizer-sidebar');
    expect(sidebar).not.toBeNull();
  });

  test('Sidebar has expected content', async () => {
    await page.click('.video-summarizer-icon');
    const sidebar = await page.$('#video-summarizer-sidebar');
    const sidebarContent = await sidebar.$eval('h2', el => el.textContent);
    expect(sidebarContent).toBe('Video Summarizer');
  });

  afterAll(() => browser.close());
});