export const env = {
  api: {
    baseUrl: process.env.TEST_API_URL ?? 'http://192.168.51.108:5173',
  },
  e2e: {
    baseUrl: process.env.TEST_APP_URL ?? 'http://192.168.51.108:5173',
  },
  db: {
    host: process.env.TEST_DB_HOST ?? 'localhost',
    port: Number(process.env.TEST_DB_PORT ?? 5432),
    name: process.env.TEST_DB_NAME ?? 'testdb',
    user: process.env.TEST_DB_USER ?? 'postgres',
    password: process.env.TEST_DB_PASSWORD ?? '',
  },
  testUser: {
    username: process.env.TEST_USER_NAME ?? 'tester',
    password: process.env.TEST_USER_PASSWORD ?? '123456',
  },
};
