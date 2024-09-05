const { calculateTimeSaved } = require('../src/utils');

test('calculateTimeSaved returns correct value', () => {
  expect(calculateTimeSaved(10, 5)).toBe(5);
});

// Add more unit tests for your utility functions