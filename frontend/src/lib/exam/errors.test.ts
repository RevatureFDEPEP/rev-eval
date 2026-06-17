import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';
import { classifyError, ExamError, fetchWithRetry } from './errors';

const noSleep = () => Promise.resolve();

describe('classifyError', () => {
  it('treats a network failure (undefined status) as transient', () => {
    expect(classifyError(undefined)).toBe('transient');
  });

  it.each([502, 503, 504])('treats %i as transient', (status) => {
    expect(classifyError(status)).toBe('transient');
  });

  it.each([409, 410, 422])('treats %i as semantic', (status) => {
    expect(classifyError(status)).toBe('semantic');
  });

  it.each([400, 401, 403, 404, 500])('treats %i as semantic (halt, do not storm)', (status) => {
    expect(classifyError(status)).toBe('semantic');
  });
});

describe('fetchWithRetry', () => {
  it('returns the result with no retry on success', async () => {
    const fn = vi.fn().mockResolvedValue('ok');
    await expect(fetchWithRetry(fn, { sleep: noSleep })).resolves.toBe('ok');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('retries a transient failure then succeeds', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, 'unavailable', ''))
      .mockResolvedValue('ok');
    await expect(fetchWithRetry(fn, { sleep: noSleep })).resolves.toBe('ok');
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('does NOT retry a semantic failure — throws immediately', async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(409, 'conflict', ''));
    await expect(fetchWithRetry(fn, { sleep: noSleep })).rejects.toBeInstanceOf(ExamError);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('rethrows as ExamError after exhausting transient retries', async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(502, 'bad gateway', ''));
    const err = (await fetchWithRetry(fn, { maxRetries: 2, sleep: noSleep }).catch(
      (e) => e,
    )) as ExamError;
    expect(err).toBeInstanceOf(ExamError);
    expect(err.kind).toBe('transient');
    expect(fn).toHaveBeenCalledTimes(3); // initial + 2 retries
  });
});
