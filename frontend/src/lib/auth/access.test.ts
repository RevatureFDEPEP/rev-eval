import { describe, expect, it } from 'vitest';
import { resolveAccess } from './access';

describe('resolveAccess', () => {
  it('allows TRAINER into /admin/*', () => {
    expect(resolveAccess('/admin/dashboard', 'TRAINER')).toBe('allow');
  });

  it('forbids PARTICIPANT from /admin/*', () => {
    expect(resolveAccess('/admin/dashboard', 'PARTICIPANT')).toBe('forbidden');
  });

  it('forbids ADMIN from /admin/* (matches TRAINER-only backend gate)', () => {
    expect(resolveAccess('/admin/dashboard', 'ADMIN')).toBe('forbidden');
  });

  it('is case-insensitive on the role claim', () => {
    expect(resolveAccess('/admin/dashboard', 'trainer')).toBe('allow');
  });

  it('keeps /trainer open to TRAINER and ADMIN', () => {
    expect(resolveAccess('/trainer/dashboard', 'TRAINER')).toBe('allow');
    expect(resolveAccess('/trainer/dashboard', 'ADMIN')).toBe('allow');
    expect(resolveAccess('/trainer/dashboard', 'PARTICIPANT')).toBe('forbidden');
  });

  it('allows unprotected paths for any role', () => {
    expect(resolveAccess('/results/abc', 'PARTICIPANT')).toBe('allow');
    expect(resolveAccess('/take/1', 'TRAINER')).toBe('allow');
  });
});
