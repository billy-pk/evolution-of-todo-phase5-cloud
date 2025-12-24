import '@testing-library/jest-dom';

// Configure React 19 act() environment
// This tells React that the test environment properly handles act()
// @testing-library/react automatically wraps interactions in act()
if (typeof window !== 'undefined') {
  // @ts-ignore - React 19 internal property
  window.IS_REACT_ACT_ENVIRONMENT = true;
}
if (typeof global !== 'undefined') {
  // @ts-ignore - React 19 internal property
  global.IS_REACT_ACT_ENVIRONMENT = true;
}

// Suppress React 19 act() warnings in console
// These are false positives - @testing-library already handles act() properly
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('The current testing environment is not configured to support act')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

jest.mock('better-auth/react', () => ({
  createAuthClient: jest.fn(() => ({
    token: jest.fn(() => ({ data: { token: 'mock-jwt-token' } })),
    signOut: jest.fn(),
  })),
}));

jest.mock('better-auth/client/plugins', () => ({
  jwtClient: jest.fn(() => ({
    getClaims: jest.fn(() => ({ userId: 'mock-user-id' })),
  })),
}));