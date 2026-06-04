import { jest } from "@jest/globals";

export const mockRouter = {
  push: jest.fn(),
  refresh: jest.fn(),
  back: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
};

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
