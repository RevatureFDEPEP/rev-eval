import { jest } from "@jest/globals";

export const mockRouter = {
  push: jest.fn(),
  refresh: jest.fn(),
  back: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
};

export function resetMockRouter() {
  mockRouter.push.mockReset();
  mockRouter.refresh.mockReset();
  mockRouter.back.mockReset();
  mockRouter.replace.mockReset();
  mockRouter.prefetch.mockReset();
}

export function useRouter() {
  return mockRouter;
}

export function usePathname() {
  return "/";
}

export function useParams() {
  return {};
}

export function useSearchParams() {
  return new URLSearchParams();
}
