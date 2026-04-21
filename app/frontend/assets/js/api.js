/* ============================================================
   API — cliente centralizado para o backend FastAPI
   ============================================================ */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "/api"
  : "https://gestao-contratos-sebrae.onrender.com/api";

const IS_RENDER = !["localhost","127.0.0.1"].includes(window.location.hostname);

function getToken() {
  return localStorage.getItem("token");
}

/* ── Banner de "servidor acordando" ──────────────────────────────────────── */
let _wakeupBanner = null;
function _mostrarAcordando() {
  if (_wakeupBanner) return;
  _wakeupBanner = document.createElement("div");
  _wakeupBanner.id = "banner-acordando";
  _wakeupBanner.style.cssText =
    "position:fixed;top:0;left:0;right:0;z-index:9999;background:#1565C0;color:#fff;" +
    "text-align:center;padding:10px;font-size:13px;font-weight:600;" +
    "box-shadow:0 2px 8px rgba(0,0,0,.3)";
  _wakeupBanner.innerHTML =
    "⏳ Servidor acordando (pode levar até 40 s na primeira vez)… Aguarde, a página carregará automaticamente.";
  document.body.prepend(_wakeupBanner);
}
function _removerAcordando() {
  if (_wakeupBanner) { _wakeupBanner.remove(); _wakeupBanner = null; }
}

/* ── Fetch com retry automático (para cold start do Render) ──────────────── */
async function apiFetch(path, options = {}, _tentativa = 1) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const MAX_TENTATIVAS = 5;          // tenta até 5 vezes
  const DELAYS = [3000, 6000, 10000, 15000]; // esperas entre tentativas

  try {
    const res = await fetch(API_BASE + path, { ...options, headers });
    _removerAcordando();

    if (res.status === 401) {
      localStorage.clear();
      window.location.href = "/";
      return;
    }

    const data = res.headers.get("content-type")?.includes("application/json")
      ? await res.json()
      : await res.text();

    if (!res.ok) {
      const msg = data?.detail || data || `Erro ${res.status}`;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;

  } catch (err) {
    // Só faz retry em erros de rede ("Failed to fetch"), não em erros HTTP
    const ehErroDeRede = err instanceof TypeError && err.message.toLowerCase().includes("fetch");

    if (ehErroDeRede && IS_RENDER && _tentativa < MAX_TENTATIVAS) {
      _mostrarAcordando();
      const delay = DELAYS[_tentativa - 1] ?? 15000;
      await new Promise(r => setTimeout(r, delay));
      return apiFetch(path, options, _tentativa + 1);
    }

    _removerAcordando();
    throw err;
  }
}

/* ── Keep-alive: pinga o servidor a cada 12 min para evitar hibernação ───── */
if (IS_RENDER) {
  setInterval(() => {
    fetch(API_BASE + "/auth/ping").catch(() => {});
  }, 12 * 60 * 1000); // 12 minutos
}

/* ── API pública ─────────────────────────────────────────────────────────── */
const api = {
  // Auth
  login: (login, senha) =>
    apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ login, senha }) }),

  me: () => apiFetch("/usuarios/me"),

  // Processos
  listarProcessos: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ""))
    ).toString();
    return apiFetch(`/processos${qs ? "?" + qs : ""}`);
  },
  dashboard: () => apiFetch("/processos/dashboard"),
  obterProcesso: (id) => apiFetch(`/processos/${id}`),
  criarProcesso: (data) =>
    apiFetch("/processos", { method: "POST", body: JSON.stringify(data) }),
  atualizarProcesso: (id, data) =>
    apiFetch(`/processos/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  excluirProcesso: (id) =>
    apiFetch(`/processos/${id}`, { method: "DELETE" }),
  resolverEtapas: (demanda_id, data_atribuicao, atribuido_para_id) =>
    apiFetch("/processos/resolver-etapas", {
      method: "POST",
      body: JSON.stringify({ demanda_id, data_atribuicao, atribuido_para_id }),
    }),

  // Configurações
  unidades:       () => apiFetch("/config/unidades"),
  distribuidores: () => apiFetch("/config/distribuidores"),
  atribuidos:     () => apiFetch("/config/atribuidos"),
  demandas:       () => apiFetch("/config/demandas"),
  garantias:      () => apiFetch("/config/garantias"),
  prazos:         () => apiFetch("/config/prazos"),
  etapasDemanda:  (id) => apiFetch(`/config/demandas/${id}/etapas`),
  criarDemanda:   (data) =>
    apiFetch("/config/demandas", { method: "POST", body: JSON.stringify(data) }),
  excluirDemanda: (id) =>
    apiFetch(`/config/demandas/${id}`, { method: "DELETE" }),

  // Feriados
  listarFeriados: () => apiFetch("/feriados"),
  criarFeriado:   (data) =>
    apiFetch("/feriados", { method: "POST", body: JSON.stringify(data) }),
  atualizarFeriado: (id, data) =>
    apiFetch(`/feriados/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  excluirFeriado: (id) =>
    apiFetch(`/feriados/${id}`, { method: "DELETE" }),

  // Usuários
  listarUsuarios: () => apiFetch("/usuarios"),
  criarUsuario:   (data) =>
    apiFetch("/usuarios", { method: "POST", body: JSON.stringify(data) }),
  atualizarUsuario: (id, data) =>
    apiFetch(`/usuarios/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};
