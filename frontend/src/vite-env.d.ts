interface ImportMetaEnv {
  /** 1 — ходить в API и вне Telegram (бэкенд с DEBUG=1 и DEV_USER_ID). */
  readonly VITE_USE_API?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
