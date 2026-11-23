const TOKEN_KEY = 'rental_token';
export async function api(path, options = {}) {
  const headers = {'Content-Type':'application/json', ...(options.headers || {})};
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`/api${path}`, {...options, headers});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `请求失败 ${response.status}`);
  return data;
}
export function saveSession(data){ localStorage.setItem(TOKEN_KEY, data.access_token); localStorage.setItem('rental_user', JSON.stringify(data.user)); }
export function clearSession(){ localStorage.removeItem(TOKEN_KEY); localStorage.removeItem('rental_user'); }
export function session(){ const token = localStorage.getItem(TOKEN_KEY); return token ? JSON.parse(localStorage.getItem('rental_user') || '{}') : null; }
