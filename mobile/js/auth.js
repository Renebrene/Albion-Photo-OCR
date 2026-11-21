/**
 * Authentication module.
 *
 * Вход — по логину и паролю из базы PhotoBAse (`public.users`): сервер
 * проверяет `password_hash` (scrypt) и выдаёт токен сессии. Никаких
 * демо-пользователей: без запущенного бэкенда вход невозможен.
 */

import { api } from './api.js';

// Роли → scopes. Сервер проверяет права сам; карта нужна только чтобы
// мобильный UI показывал доступные действия роли (как десктоп).
const ROLE_SCOPES = {
  'Администратор': ['*'],
  'Менеджер': [
    'read',
    'collections:write',
    'searches:write',
    'upload:write',
    'photos:write',
    'jobs:read',
    'jobs:write',
    'addresses:write',
    'originals',
  ],
  'Гость': ['read'],
};

const auth = {
  user: null,
  authEnabled: false,

  /** Восстановить сессию из localStorage (токен → /auth/me). */
  async init() {
    if (!api.getToken()) {
      this.user = null;
      this.authEnabled = false;
      return null;
    }

    try {
      this.user = await api.getCurrentUser();
      this.authEnabled = !!this.user;
    } catch (error) {
      // Токен просрочен или отозван — начинаем с экрана входа.
      api.setToken(null);
      this.user = null;
      this.authEnabled = false;
    }

    return this.user;
  },

  /** Вход по учётным данным PhotoBAse. */
  async login(name, password) {
    const user = await api.login(name, password);

    if (!user) {
      throw new Error('сервер не вернул пользователя');
    }

    this.user = user;
    this.authEnabled = true;

    return user;
  },

  async logout() {
    await api.logout();
    this.user = null;
    this.authEnabled = false;
  },

  isLoggedIn() {
    return this.authEnabled && !!this.user;
  },

  getRole() {
    return this.user?.role || 'Гость';
  },

  /** Есть ли у роли право (сервер всё равно проверит сам). */
  hasScope(scope) {
    const scopes = this.user?.scopes || ROLE_SCOPES[this.getRole()] || [];

    return scopes.includes('*') || scopes.includes(scope);
  },
};

export { auth };
