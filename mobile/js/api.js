/**
 * API client for the PhotoBAse mobile PWA.
 *
 * Контракт — тот же FastAPI, что обслуживает десктопную SPA. Страница
 * раздаётся тем же процессом (/mobile/), поэтому запросы same-origin:
 * `Authorization` уходит заголовком, куки сессии — автоматически.
 *
 * База API:
 *   - страница открыта с бэкенда: порт 8010 или домен за TLS-прокси
 *     (https://albion-base.cloudpub.ru — порт пустой) → /api/v1 (same origin)
 *   - страница на отдельном dev-сервере статики (8080/5173/3000)
 *     → <protocol>//<host>:8010/api/v1
 *   - window.SCENE_API_BASE → явное переопределение
 */

const DEFAULT_API_PORT = '8010';
const DEV_STATIC_PORTS = new Set(['3000', '5173', '8080']);

function resolveApiBase() {
  if (typeof window !== 'undefined' && window.SCENE_API_BASE) {
    return String(window.SCENE_API_BASE).replace(/\/$/, '');
  }

  const { port, protocol, hostname } = window.location;

  // Порт пустой (https за прокси) или 8010 — страницу отдал сам бэкенд.
  // Любой другой порт, кроме известных dev-серверов, тоже считаем
  // same-origin: внешний прокси может слушать 8443/10000 и т.п.
  if (!port || port === DEFAULT_API_PORT || !DEV_STATIC_PORTS.has(port)) {
    return '/api/v1';
  }

  return `${protocol}//${hostname}:${DEFAULT_API_PORT}/api/v1`;
}

const API_BASE = resolveApiBase();

/** Append params, repeating keys for arrays (`address=a&address=b`). */
function buildQuery(params = {}) {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;

    if (Array.isArray(value)) {
      for (const item of value) {
        if (item === undefined || item === null || item === '') continue;
        search.append(key, String(item));
      }
    } else {
      search.append(key, String(value));
    }
  }

  const query = search.toString();

  return query ? `?${query}` : '';
}

class ApiClient {
  constructor() {
    this.token = null;
    this.baseUrl = API_BASE;
  }

  /** Remember the session token (also used by <img> through the cookie). */
  setToken(token) {
    this.token = token || null;

    if (token) {
      localStorage.setItem('photobase_token', token);
    } else {
      localStorage.removeItem('photobase_token');
    }
  }

  getToken() {
    if (!this.token) {
      this.token = localStorage.getItem('photobase_token');
    }

    return this.token;
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  async request(url, options = {}) {
    const headers = { ...options.headers };
    const token = this.getToken();

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${this.baseUrl}${url}`, {
      ...options,
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body && (body.detail || body.message);
      const error = new Error(
        typeof detail === 'string' && detail
          ? detail
          : `HTTP ${response.status} ${response.statusText}`,
      );
      error.status = response.status;
      error.body = body;
      throw error;
    }

    if (response.status === 204) return null;

    return response.json();
  }

  // ===== Auth =====

  /** POST /auth/login → user (token сохраняется отдельно). */
  async login(name, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ name, password }),
    });

    if (data && data.token) {
      this.setToken(data.token);
    }

    return data ? data.user || null : null;
  }

  /** GET /auth/me → user | null. */
  async getCurrentUser() {
    const data = await this.request('/auth/me');

    return data && data.user ? data.user : null;
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (error) {
      // Выход не должен падать из-за недоступного сервера.
    } finally {
      this.setToken(null);
    }
  }

  // ===== Photos =====

  /**
   * GET /photos → { items, next_cursor, total }.
   *
   * Поддерживаемые фильтры: q, address[] (addr:<id>), client[], brand, tag,
   * category, date_from, date_to, date_mode (upload|capture), collection_id,
   * group (screens|small|rostov|roads|cities), sort, order, cursor, limit.
   */
  async fetchPhotos(params = {}) {
    return this.request(`/photos${buildQuery(params)}`);
  }

  /**
   * GET /photos/dates → { items: [{date, photos, sample_photo_id}], total }.
   * Дни съёмки за период — плитки вкладки «По датам».
   */
  async fetchPhotoDates(params = {}) {
    return this.request(`/photos/dates${buildQuery(params)}`);
  }

  /** URL превью для <img> — авторизация кукой сессии (GET разрешён). */
  previewUrl(photoId, size = 'small') {
    return `${this.baseUrl}/photos/${encodeURIComponent(photoId)}/previews/${size}`;
  }

  /** GET /photos/{id}/original → blob (нужен scope `originals`). */
  async fetchOriginal(photoId) {
    const headers = {};
    const token = this.getToken();

    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await fetch(
      `${this.baseUrl}/photos/${encodeURIComponent(photoId)}/original`,
      { headers, credentials: 'include' },
    );

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body && (body.detail || body.message);
      const error = new Error(
        typeof detail === 'string' && detail
          ? detail
          : `HTTP ${response.status} ${response.statusText}`,
      );
      error.status = response.status;
      throw error;
    }

    return response.blob();
  }

  // ===== Addresses =====

  /** GET /addresses → { items: [{ address, ids, name, count, … }] }. */
  async fetchAddresses(params = {}) {
    return this.request(`/addresses${buildQuery(params)}`);
  }

  // ===== Collections =====

  /** GET /collections → { items: [{ collection_id, name, scope, members }] }. */
  async fetchCollections() {
    return this.request('/collections');
  }

  /** GET /collections/{id}/members → { items: [value, …] }. */
  async getCollectionMembers(collectionId, memberType = 'photo') {
    return this.request(
      `/collections/${collectionId}/members?member_type=${memberType}`,
    );
  }

  /** DELETE /collections/{id} — удаление подборки (scope collections:write). */
  async deleteCollection(collectionId) {
    return this.request(
      `/collections/${encodeURIComponent(collectionId)}`,
      { method: 'DELETE' },
    );
  }

  // ===== Favorites =====

  /** GET /favorites → { collection_id, photo_ids, count }. */
  async getFavorites() {
    return this.request('/favorites');
  }

  /** POST /favorites с телом { photo_ids: [...] }. */
  async addFavorites(photoIds) {
    return this.request('/favorites', {
      method: 'POST',
      body: JSON.stringify({ photo_ids: photoIds }),
    });
  }

  /** DELETE /favorites/{photo_id}. */
  async removeFavorite(photoId) {
    return this.request(`/favorites/${encodeURIComponent(photoId)}`, {
      method: 'DELETE',
    });
  }

  // ===== Search =====

  /** GET /search/suggestions?q=… (автодополнение). */
  async getSearchSuggestions(query) {
    return this.request(`/search/suggestions${buildQuery({ q: query })}`);
  }

  // ===== Archive =====

  /**
   * POST /photos/archive {items:[{photo_id,name}]} → ZIP-blob.
   * Нужен scope `originals`; сервер собирает архив из оригиналов.
   */
  async fetchArchive(items) {
    const headers = { 'Content-Type': 'application/json' };
    const token = this.getToken();

    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await fetch(`${this.baseUrl}/photos/archive`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ items }),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body && (body.detail || body.message);
      const error = new Error(
        typeof detail === 'string' && detail
          ? detail
          : `HTTP ${response.status} ${response.statusText}`,
      );
      error.status = response.status;
      throw error;
    }

    return response.blob();
  }
}

const api = new ApiClient();

export { api };
