module.exports = {
  testEnvironment: 'jsdom',
  testEnvironmentOptions: {
    customExportConditions: [''],
  },
  testPathIgnorePatterns: ['/.next/'],
  collectCoverageFrom: [
    'components/**/*.tsx',
    'lib/**/*.ts',
    '!components/**/*.test.tsx',
    '!lib/**/*.test.ts',
  ],
  setupFilesAfterEnv: ['<rootDir>/setupTests.ts'],
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', {
      presets: [
        ['next/babel', {
          'preset-react': {
            runtime: 'automatic',
            importSource: 'react'
          }
        }]
      ]
    }],
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(better-auth|@babel/runtime))',
    '^.+\\.module\\.(css|sass|scss)$',
  ],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  // Suppress specific console errors from React 19 act() warnings
  // These are false positives in the test environment
  silent: false,
  verbose: true,
};