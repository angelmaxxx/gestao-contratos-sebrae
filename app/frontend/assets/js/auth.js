/* ============================================================
   Auth — gerenciamento de sessão
   ============================================================ */

function getSessao() {
  try {
    return JSON.parse(localStorage.getItem("sessao") || "null");
  } catch { return null; }
}

function isAdmin() {
  return getSessao()?.perfil === "admin";
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/";
    return false;
  }
  return true;
}

function initLayout() {
  if (!requireAuth()) return;
  const sessao = getSessao();
  if (!sessao) return;

  // Marca perfil no body para CSS
  if (sessao.perfil === "admin") document.body.classList.add("is-admin");

  // Preenche topbar
  const elUser = document.getElementById("topbar-user");
  const elPerfil = document.getElementById("topbar-perfil");
  if (elUser)   elUser.textContent = sessao.nome;
  if (elPerfil) elPerfil.textContent = sessao.perfil === "admin" ? "Admin" : "Usuário";

  // Marca aba ativa
  const path = window.location.pathname.replace("/", "").replace(".html", "") || "dashboard";
  document.querySelectorAll(".navbar a").forEach(a => {
    a.classList.remove("active");
    if (a.dataset.page === path) a.classList.add("active");
  });
}

function logout() {
  localStorage.clear();
  window.location.href = "/";
}

/* ── Toast ── */
function toast(msg, tipo = "info") {
  let container = document.getElementById("toast");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast";
    document.body.appendChild(container);
  }
  const el = document.createElement("div");
  el.className = `toast-item ${tipo}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ── Utilitários de data ── */
function formatDate(str) {
  if (!str) return "—";
  const [y, m, d] = str.split("T")[0].split("-");
  return `${d}/${m}/${y}`;
}

function formatDatetime(str) {
  if (!str) return "—";
  const d = new Date(str);
  return d.toLocaleString("pt-BR");
}

/* ── Badge de status ── */
function badgeStatus(st) {
  if (!st || st === "N/A") return `<span class="badge em-aberto">${st || "—"}</span>`;
  if (st.includes("FORA"))      return `<span class="badge fora-prazo">${st}</span>`;
  if (st.includes("EM ABERTO")) return `<span class="badge no-prazo">${st}</span>`;
  if (st === "REALIZADO NO PRAZO") return `<span class="badge realizado-ok">${st}</span>`;
  if (st.includes("REALIZADO")) return `<span class="badge realizado-atraso">${st}</span>`;
  if (st.includes("PENDÊNCIA")) return `<span class="badge pendencia">${st}</span>`;
  return `<span class="badge em-aberto">${st}</span>`;
}

/* ── Etapa atual (para dashboard) ── */
function etapaAtual(p) {
  if (!p.data_atribuicao) return "Distribuição";
  if (!p.nao_aplica_validacao && !p.data_validar) return "Aguard. Validação";
  if (!p.nao_aplica_juridico  && !p.fim_juridico) return "Jurídico";
  if (!p.nao_aplica_assinatura && !p.fim_assinatura) return "Assinatura";
  if (!p.nao_aplica_cadastro  && !p.fim_cadastro) return "Cadastro";
  return "Concluído";
}
