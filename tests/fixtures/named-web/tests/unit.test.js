import { expect, test } from 'vitest';
import { countAfterClick } from '../src/widget.js';

test('click increments the count', () => {
  expect(countAfterClick(0)).toBe(1);
});
