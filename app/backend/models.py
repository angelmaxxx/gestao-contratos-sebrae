from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


# ============================================================
# AUTH
# ============================================================

class LoginRequest(BaseModel):
    login: str
    senha: str


class TokenResponse(BaseModel):
    token: str
    perfil: str
    nome: str


# ============================================================
# USUÁRIOS
# ============================================================

class UsuarioCreate(BaseModel):
    login: str
    nome: str
    perfil: str
    senha: str

    @field_validator("perfil")
    @classmethod
    def perfil_valido(cls, v):
        if v not in ("admin", "usuario"):
            raise ValueError("Perfil deve ser 'admin' ou 'usuario'")
        return v


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    perfil: Optional[str] = None
    senha: Optional[str] = None
    ativo: Optional[bool] = None


class UsuarioOut(BaseModel):
    id: str
    login: str
    nome: str
    perfil: str
    ativo: bool
    ultimo_acesso: Optional[datetime] = None
    criado_em: Optional[datetime] = None


# ============================================================
# CONFIGURAÇÕES
# ============================================================

class ItemNome(BaseModel):
    nome: str


class FeriadoCreate(BaseModel):
    data: date
    descricao: str
    tipo: str

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v):
        validos = ("FERIADO_NACIONAL", "FERIADO_DISTRITAL", "RECESSO_SEBRAE")
        if v not in validos:
            raise ValueError(f"Tipo deve ser um de: {validos}")
        return v


class FeriadoOut(BaseModel):
    id: int
    data: date
    dia_semana: Optional[str] = None
    descricao: str
    tipo: str
    ativo: bool


class PrazoEtapaUpdate(BaseModel):
    etapa: str
    dias_uteis: int


class PrazoValidacaoUpdate(BaseModel):
    dias_uteis: int


# ============================================================
# PROCESSOS
# ============================================================

class ProcessoCreate(BaseModel):
    numero_processo: str
    instrumento: Optional[str] = None
    contratada: Optional[str] = None
    unidade_id: Optional[int] = None
    data_entrada: Optional[date] = None
    distribuidor_id: Optional[int] = None
    tem_garantia: Optional[str] = None
    demanda_id: Optional[int] = None

    data_atribuicao: Optional[date] = None
    atribuido_para_id: Optional[int] = None

    data_validar: Optional[date] = None
    nao_aplica_validacao: bool = False
    validador_id: Optional[int] = None

    inicio_juridico: Optional[date] = None
    nao_aplica_juridico: bool = False
    fim_juridico: Optional[date] = None

    atrib_assinatura_id: Optional[int] = None
    nao_aplica_assinatura: bool = False
    data_atrib_assinatura: Optional[date] = None
    fim_assinatura: Optional[date] = None

    atrib_cadastro_id: Optional[int] = None
    nao_aplica_cadastro: bool = False
    data_atrib_cadastro: Optional[date] = None
    fim_cadastro: Optional[date] = None

    comentario: Optional[str] = None


class ProcessoUpdate(ProcessoCreate):
    numero_processo: Optional[str] = None


# Campos calculados — só retornados para admin
class CalcEtapa(BaseModel):
    prazo_du: Optional[int] = None
    prev_fim: Optional[date] = None
    status: Optional[str] = None
    tempo_real: Optional[int] = None


class ProcessoCalculos(BaseModel):
    distribuicao: CalcEtapa
    validacao: CalcEtapa
    juridico: CalcEtapa
    assinatura: CalcEtapa
    cadastro: CalcEtapa
    prazo_total: Optional[int] = None
    prev_fim_total: Optional[date] = None
    status_total: Optional[str] = None
    responsabilidade: Optional[str] = None
    tempo_total: Optional[int] = None


class ProcessoOut(BaseModel):
    id: int
    numero_processo: str
    instrumento: Optional[str] = None
    contratada: Optional[str] = None
    unidade_id: Optional[int] = None
    unidade_nome: Optional[str] = None
    data_entrada: Optional[date] = None
    distribuidor_id: Optional[int] = None
    distribuidor_nome: Optional[str] = None
    tem_garantia: Optional[str] = None
    demanda_id: Optional[int] = None
    demanda_nome: Optional[str] = None

    data_atribuicao: Optional[date] = None
    atribuido_para_id: Optional[int] = None
    atribuido_para_nome: Optional[str] = None

    data_validar: Optional[date] = None
    nao_aplica_validacao: bool = False
    validador_id: Optional[int] = None
    validador_nome: Optional[str] = None

    inicio_juridico: Optional[date] = None
    nao_aplica_juridico: bool = False
    fim_juridico: Optional[date] = None

    atrib_assinatura_id: Optional[int] = None
    nao_aplica_assinatura: bool = False
    atrib_assinatura_nome: Optional[str] = None
    data_atrib_assinatura: Optional[date] = None
    fim_assinatura: Optional[date] = None

    atrib_cadastro_id: Optional[int] = None
    nao_aplica_cadastro: bool = False
    atrib_cadastro_nome: Optional[str] = None
    data_atrib_cadastro: Optional[date] = None
    fim_cadastro: Optional[date] = None

    comentario: Optional[str] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    # Apenas para admin
    calculos: Optional[ProcessoCalculos] = None


class ResolverEtapasRequest(BaseModel):
    demanda_id: int
    data_atribuicao: Optional[date] = None
    atribuido_para_id: Optional[int] = None


class ResolverEtapasResponse(BaseModel):
    etapas: dict  # etapa -> {'aplica': bool, 'auto': bool, 'valor': any}
    is_cadastro: bool
