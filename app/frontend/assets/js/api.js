/* ============================================================
   API — cliente centralizado para o backend FastAPI
   ============================================================ */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "/api"
  : "https://gestao-contratos-sebrae.onrender.com/api";

function getToken() {
  return localStorage.getItem("token");
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(API_BASE + path, { ...options, headers });

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
}

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
