export const env = {
  api: {
    baseUrl: process.env.TEST_API_URL ?? 'http://localhost:3000',
  },
  e2e: {
    baseUrl: process.env.TEST_APP_URL ?? 'http://localhost:5173',
  },
  db: {
    host: process.env.TEST_DB_HOST ?? 'localhost',
    port: Number(process.env.TEST_DB_PORT ?? 5432),
    name: process.env.TEST_DB_NAME ?? 'testdb',
    user: process.env.TEST_DB_USER ?? 'postgres',
    password: process.env.TEST_DB_PASSWORD ?? '',
  },
  testUser: {
    email: process.env.TEST_USER_EMAIL ?? 'test@example.com',
    password: process.env.TEST_USER_PASSWORD ?? 'Abc123456',
  },
};
