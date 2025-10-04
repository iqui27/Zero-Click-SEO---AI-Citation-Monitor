module.exports = {
    root: true,
    parser: '@typescript-eslint/parser',
    parserOptions: { project: ['./tsconfig.json'], tsconfigRootDir: __dirname },
    plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
    extends: [
      'eslint:recommended',
      'plugin:@typescript-eslint/recommended',
      'plugin:react-hooks/recommended',
      'plugin:react-refresh/recommended',
    ],
    env: { browser: true, es2021: true },
    settings: { react: { version: 'detect' } },
    ignorePatterns: ['dist', 'node_modules'],
    rules: {
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  }