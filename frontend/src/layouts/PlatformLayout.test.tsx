import { describe, expect, it } from 'vitest';

import { NAV_ITEMS, selectedNavKey } from './PlatformLayout';

function itemKeys(items: typeof NAV_ITEMS): string[] {
  return items.flatMap((item) => {
    if (!item || ('type' in item && item.type === 'divider')) return [];
    const children = 'children' in item ? item.children : undefined;
    return [String(item.key), ...itemKeys(children ?? [])];
  });
}

describe('scenario navigation and compatibility routes', () => {
  const keys = itemKeys(NAV_ITEMS);

  it('keeps configured scenarios and the shared antenna library in navigation', () => {
    expect(keys).toContain('/scenarios');
    expect(keys).toContain('/scenarios/assets/antenna');
  });

  it('does not expose legacy UE, radio, or association pages as navigation entries', () => {
    expect(keys).not.toContain('/scenarios/ue');
    expect(keys).not.toContain('/scenarios/radio');
    expect(keys).not.toContain('/scenarios/association');
  });

  it('does not falsely select Overview when a compatibility-only URL is opened directly', () => {
    expect(selectedNavKey('/scenarios/ue')).toBe('');
    expect(selectedNavKey('/scenarios/radio')).toBe('');
    expect(selectedNavKey('/scenarios/association')).toBe('');
  });
});
