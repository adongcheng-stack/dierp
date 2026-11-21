module.exports = {
  root: true,
  env: { browser: true, es2021: true, node: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['@typescript-eslint'],
  ignorePatterns: [
    'dist/', 'dist-*/', 'node_modules/', 'e2e/', '*.generated.ts',
    'src/mock/snapshot.json', 'scripts/',
  ],
  rules: {
    // 演示代码里存在少量 any（mock 数据、动态表单），不阻断构建
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    '@typescript-eslint/no-empty-function': 'off',
    'no-empty': ['error', { allowEmptyCatch: true }],
  },
}
