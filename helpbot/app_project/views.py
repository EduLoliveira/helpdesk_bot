from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from functools import wraps
import json
import threading
import time
import logging
import re
from django.core.exceptions import ValidationError, PermissionDenied
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils.html import strip_tags
import html as html_escape
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime

from .models import Usuario, Chamado, Departamento, InteracaoChamado, Notificacao
from .bot_dialogos import bot_dialogos

# Configurar logging
logger = logging.getLogger(__name__)

class SecurityManager:
    """Gerenciador centralizado de medidas de segurança"""
    
    @staticmethod
    def sanitize_input(text, max_length=500, allow_html=False):
        """Sanitiza entrada de usuário removendo ou escapando conteúdo perigoso"""
        if not text:
            return ""
        
        # Remove tags HTML se não permitido
        if not allow_html:
            clean_text = strip_tags(str(text))
            # Escapa caracteres especiais
            clean_text = html_escape.escape(clean_text)
        else:
            clean_text = str(text)
        
        # Limita o tamanho
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length]
            
        return clean_text.strip()
    
    @staticmethod
    def validate_username(username):
        """Valida formato do username"""
        if not username or len(username) < 3:
            raise ValidationError("Username deve ter pelo menos 3 caracteres")
        
        if len(username) > 30:
            raise ValidationError("Username muito longo (máximo 30 caracteres)")
            
        # Permite apenas letras, números e alguns caracteres especiais
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username contém caracteres inválidos. Use apenas letras, números, '.', '-' e '_'")
        
        # Previne usernames comuns que podem ser usados em ataques
        blocked_usernames = ['admin', 'administrator', 'root', 'system', 'suporte', 'support']
        if username.lower() in blocked_usernames:
            raise ValidationError("Este username não está disponível")
        
        return username
    
    @staticmethod
    def validate_codigo_suporte(codigo):
        """Valida código de suporte - CORRIGIDO PARA 6 DÍGITOS E COLABORADORES"""
        try:
            # Remove espaços e converte para string
            codigo_str = str(codigo).strip()
            
            # Verifica se está vazio
            if not codigo_str:
                raise ValidationError("Código de suporte é obrigatório")
            
            # Verifica se é um número válido
            if not codigo_str.isdigit():
                raise ValidationError("Código de suporte deve conter apenas números")
            
            codigo_int = int(codigo_str)
            
            # ✅ CORREÇÃO: Aceita códigos de 6 dígitos (100000-199999 = Suporte, 200000-999999 = Colaborador)
            if codigo_int < 100000 or codigo_int > 999999:
                raise ValidationError("Código de suporte deve ter 6 dígitos (ex: 100001 para suporte, 200001 para colaborador)")
            
            return codigo_int
        except (ValueError, TypeError) as e:
            raise ValidationError("Código de suporte deve ser um número válido de 6 dígitos")
    
    @staticmethod
    def validate_uuid(uuid_string):
        """Valida formato UUID"""
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        return bool(uuid_pattern.match(str(uuid_string)))
    
    @staticmethod
    def prevent_brute_force(request, operation_type, max_attempts=5, window_seconds=300):
        """Prevenção básica contra ataques de força bruta"""
        from django.core.cache import cache
        
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        key = f"brute_force_{operation_type}_{client_ip}"
        attempts = cache.get(key, 0)
        
        if attempts >= max_attempts:
            logger.warning(f"Brute force detectado: {client_ip} - {operation_type}")
            return False
            
        cache.set(key, attempts + 1, window_seconds)
        return True

# Instância global do gerenciador de segurança
security = SecurityManager()

def rate_limit(max_requests=100, window=3600):
    """
    Decorator para limitar taxa de requisições
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not settings.DEBUG:  # Só aplica em produção
                from django.core.cache import cache
                
                client_ip = request.META.get('REMOTE_ADDR', 'unknown')
                key = f"rate_limit_{view_func.__name__}_{client_ip}"
                
                current = cache.get(key, 0)
                if current >= max_requests:
                    logger.warning(f"Rate limit excedido: {client_ip} - {view_func.__name__}")
                    return JsonResponse({
                        'success': False,
                        'message': 'Limite de requisições excedido. Tente novamente mais tarde.'
                    }, status=429)
                
                cache.set(key, current + 1, window)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def usuario_required(view_func):
    """Decorator para verificar se o usuário está cadastrado com segurança reforçada"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'usuario_id' not in request.session:
            logger.warning("Tentativa de acesso sem sessão de usuário")
            return redirect('home')
        
        try:
            # Validar UUID do usuário
            usuario_id = request.session['usuario_id']
            if not security.validate_uuid(usuario_id):
                logger.warning(f"ID de usuário inválido na sessão: {usuario_id}")
                request.session.flush()
                return redirect('home')
            
            # ✅ CORREÇÃO CRÍTICA: Buscar usuário sem usar get_object_or_404 que pode causar problemas
            try:
                usuario = Usuario.objects.get(id_usuario=usuario_id)
                request.usuario = usuario
                return view_func(request, *args, **kwargs)
            except Usuario.DoesNotExist:
                logger.warning(f"Usuário não encontrado na sessão: {usuario_id}")
                request.session.flush()
                return redirect('home')
            
        except Exception as e:
            logger.error(f"Erro no decorator de usuário: {str(e)}")
            request.session.flush()
            return redirect('home')
    return _wrapped_view

@require_http_methods(["GET", "POST"])
@rate_limit(max_requests=30, window=3600)
def home(request):
    """Página inicial com formulário para criar usuários - CORRIGIDA"""
    
    # ✅ CORREÇÃO: Verificar se usuário já está logado de forma mais simples
    if 'usuario_id' in request.session:
        try:
            # Buscar usuário diretamente
            usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
            # ✅ CORREÇÃO: Redirecionar para dashboard (não para initial.html)
            return redirect('dashboard')
        except (Usuario.DoesNotExist, ValueError):
            # Se usuário não existe, limpar sessão
            request.session.flush()
    
    # ✅ CORREÇÃO: Query separada para usuários recentes
    usuarios_recentes = list(Usuario.objects.all().order_by('-criado_em')[:3])
    
    if request.method == 'POST':
        # Prevenção contra brute force
        if not security.prevent_brute_force(request, 'user_creation', max_attempts=3, window_seconds=900):
            return render(request, 'home.html', {
                'error': 'Muitas tentativas de criação de usuário. Aguarde 15 minutos.',
                'usuarios': usuarios_recentes
            })
        
        try:
            username = security.sanitize_input(request.POST.get('username', '').strip())
            codigo_suporte = request.POST.get('codigo_suporte')
            
            logger.info(f"Tentativa de criação de usuário: {username}")
            
            # Validações básicas
            if not username or not codigo_suporte:
                return render(request, 'home.html', {
                    'error': 'Todos os campos são obrigatórios!',
                    'usuarios': usuarios_recentes
                })
            
            # Validar username
            try:
                security.validate_username(username)
            except ValidationError as e:
                return render(request, 'home.html', {
                    'error': str(e),
                    'usuarios': usuarios_recentes
                })
            
            # Validar código de suporte
            try:
                codigo_int = security.validate_codigo_suporte(codigo_suporte)
            except ValidationError as e:
                return render(request, 'home.html', {
                    'error': str(e),
                    'usuarios': usuarios_recentes
                })
            
            # Verificar se username já existe
            if Usuario.objects.filter(username=username).exists():
                return render(request, 'home.html', {
                    'error': 'Este nome de usuário já está em uso. Escolha outro.',
                    'usuarios': usuarios_recentes
                })
            
            # Determinar tipo de usuário
            if 100000 <= codigo_int <= 199999:
                tipo_usuario = 'suporte'
            else:
                tipo_usuario = 'colaborador'
            
            # Criar usuário
            usuario = Usuario.objects.create(
                username=username,
                codigo_suporte=codigo_int,
                tipo_usuario=tipo_usuario
            )
            
            logger.info(f"Usuário criado com sucesso: {username} (ID: {usuario.id_usuario}) - Tipo: {tipo_usuario}")
            
            # Configurar sessão
            request.session['usuario_id'] = str(usuario.id_usuario)
            request.session['username'] = usuario.username
            request.session['tipo_usuario'] = usuario.tipo_usuario
            request.session.set_expiry(86400)
            request.session.modified = True
            
            # ✅ CORREÇÃO: Redirecionar para dashboard após criação
            return redirect('dashboard')
            
        except IntegrityError as e:
            logger.error(f"Erro de integridade ao criar usuário: {str(e)}")
            return render(request, 'home.html', {
                'error': 'Erro ao criar usuário. Tente novamente.',
                'usuarios': usuarios_recentes
            })
        except Exception as e:
            logger.error(f"Erro inesperado ao criar usuário: {str(e)}")
            return render(request, 'home.html', {
                'error': 'Erro no sistema. Por favor, tente novamente.',
                'usuarios': usuarios_recentes
            })
    
    return render(request, 'home.html', {'usuarios': usuarios_recentes})

@require_http_methods(["GET", "POST"])
def logout_usuario(request):
    """View para fazer logout do usuário de forma segura"""
    request.session.flush()
    return redirect('home')

def criar_departamentos_iniciais():
    """Cria departamentos iniciais se não existirem"""
    departamentos = [
        {'nome': 'Atendimento', 'descricao': 'Departamento de Atendimento'},
        {'nome': 'Vendas', 'descricao': 'Departamento de Vendas'},
        {'nome': 'Marketing', 'descricao': 'Departamento de Marketing'},
        {'nome': 'TI', 'descricao': 'Tecnologia da Informação'},
        {'nome': 'Recursos Humanos', 'descricao': 'Departamento de RH'},
        {'nome': 'Financeiro', 'descricao': 'Departamento Financeiro'},
        {'nome': 'Operações', 'descricao': 'Departamento de Operações'},
    ]
    
    for dept in departamentos:
        Departamento.objects.get_or_create(
            nome=security.sanitize_input(dept['nome'], max_length=50),
            defaults={'descricao': security.sanitize_input(dept['descricao'], max_length=200)}
        )

# === LÓGICA DO DASHBOARD DE ADMIN ===
def _get_dashboard_context(request=None, page=1, items_per_page=10):
    """Função helper para buscar os dados do dashboard - CORRIGIDA"""
    
    try:
        # ✅ CORREÇÃO: Criar query inicial FRESCA
        chamados_query = Chamado.objects.all().order_by('-criado_em')
        
        # Filtros ativos
        filtros_ativos = {
            'periodo': 'todos',
            'urgencia': 'todos', 
            'departamento': 'todos',
            'status': 'todos'
        }
        
        if request and request.method == 'GET':
            # Aplicar filtros (mantém a lógica original)
            periodo = request.GET.get('periodo', 'todos')
            if periodo != 'todos':
                filtros_ativos['periodo'] = periodo
                agora = timezone.now()
                
                if periodo == 'hoje':
                    inicio_dia = timezone.localtime(agora).replace(hour=0, minute=0, second=0, microsecond=0)
                    chamados_query = chamados_query.filter(criado_em__gte=inicio_dia)
                elif periodo == 'semana':
                    uma_semana_atras = agora - timezone.timedelta(days=7)
                    chamados_query = chamados_query.filter(criado_em__gte=uma_semana_atras)
                elif periodo == 'mes':
                    um_mes_atras = agora - timezone.timedelta(days=30)
                    chamados_query = chamados_query.filter(criado_em__gte=um_mes_atras)
                elif periodo == 'trimestre':
                    tres_meses_atras = agora - timezone.timedelta(days=90)
                    chamados_query = chamados_query.filter(criado_em__gte=tres_meses_atras)
            
            urgencia = request.GET.get('urgencia', 'todos')
            if urgencia != 'todos':
                filtros_ativos['urgencia'] = urgencia
                chamados_query = chamados_query.filter(urgencia=urgencia)
            
            departamento_id = request.GET.get('departamento', 'todos')
            if departamento_id != 'todos':
                filtros_ativos['departamento'] = departamento_id
                try:
                    chamados_query = chamados_query.filter(departamento_id=departamento_id)
                except (ValueError, Departamento.DoesNotExist):
                    pass
            
            status = request.GET.get('status', 'todos')
            if status != 'todos':
                filtros_ativos['status'] = status
                chamados_query = chamados_query.filter(status=status)
        
        # ✅ CORREÇÃO: Converter para lista antes de paginar para evitar problemas
        total_chamados = chamados_query.count()
        
        # Paginação
        paginator = Paginator(chamados_query, items_per_page)
        
        try:
            chamados_paginados = paginator.page(page)
        except PageNotAnInteger:
            chamados_paginados = paginator.page(1)
        except EmptyPage:
            chamados_paginados = paginator.page(paginator.num_pages)
        
        # Consultas para os cartões
        pendentes_count = chamados_query.filter(status='em_andamento').count()
        solucionados_count = chamados_query.filter(status='resolvido').count()
        urgentes_count = chamados_query.filter(urgencia='urgente', status='em_andamento').count()
        
        # ✅ CORREÇÃO: Criar lista FRESCA para chamados recentes
        chamados_recentes = list(chamados_query[:5])

        # Lógica do Gráfico
        porcentagem_pendentes = round((pendentes_count / total_chamados) * 100) if total_chamados > 0 and pendentes_count > 0 else 0

        context = {
            'total_chamados': total_chamados,
            'pendentes_count': pendentes_count,
            'solucionados_count': solucionados_count,
            'urgentes_count': urgentes_count,
            'chamados_recentes': chamados_recentes,
            'chamados_paginados': chamados_paginados,
            'porcentagem_pendentes': porcentagem_pendentes,
            'filtros_ativos': filtros_ativos,
            'departamentos': list(Departamento.objects.all()),  # ✅ Converter para lista
        }
        
        logger.info(f"Contexto retornado: Total={total_chamados}, Pendentes={pendentes_count}")
        return context
        
    except Exception as e:
        logger.error(f"Erro em _get_dashboard_context: {str(e)}")
        # Retornar contexto vazio em caso de erro
        return {
            'total_chamados': 0,
            'pendentes_count': 0,
            'solucionados_count': 0,
            'urgentes_count': 0,
            'chamados_recentes': [],
            'chamados_paginados': [],
            'porcentagem_pendentes': 0,
            'filtros_ativos': {},
            'departamentos': [],
        }

# ✅ CORREÇÃO: View dashboard corrigida para COLABORADORES E SUPORTE
@usuario_required
@require_http_methods(["GET"])
def dashboard(request):
    """Dashboard principal - CORRIGIDA PARA COLABORADORES E SUPORTE"""
    
    # ✅ CORREÇÃO: Verificar se o usuário existe na request
    if not hasattr(request, 'usuario') or not request.usuario:
        logger.warning("Usuário não encontrado na request, redirecionando para home")
        return redirect('home')
    
    # ✅ CORREÇÃO CRÍTICA: Permitir que COLABORADORES acessem o dashboard
    # Agora tanto suporte quanto colaboradores podem acessem o dashboard
    page = request.GET.get('page', 1)
    
    try:
        # ✅ CORREÇÃO: Para colaboradores, mostrar apenas seus próprios chamados
        if request.usuario.tipo_usuario == 'colaborador':
            # Buscar apenas os chamados do usuário colaborador
            chamados_query = Chamado.objects.filter(usuario=request.usuario).order_by('-criado_em')
            
            total_chamados = chamados_query.count()
            pendentes_count = chamados_query.filter(status='em_andamento').count()
            solucionados_count = chamados_query.filter(status='resolvido').count()
            urgentes_count = chamados_query.filter(urgencia='urgente', status='em_andamento').count()
            
            # Paginação para colaboradores
            paginator = Paginator(chamados_query, 10)
            
            try:
                chamados_paginados = paginator.page(page)
            except PageNotAnInteger:
                chamados_paginados = paginator.page(1)
            except EmptyPage:
                chamados_paginados = paginator.page(paginator.num_pages)
            
            chamados_recentes = list(chamados_query[:5])
            porcentagem_pendentes = round((pendentes_count / total_chamados) * 100) if total_chamados > 0 and pendentes_count > 0 else 0
            
            context = {
                'total_chamados': total_chamados,
                'pendentes_count': pendentes_count,
                'solucionados_count': solucionados_count,
                'urgentes_count': urgentes_count,
                'chamados_recentes': chamados_recentes,
                'chamados_paginados': chamados_paginados,
                'porcentagem_pendentes': porcentagem_pendentes,
                'filtros_ativos': {},
                'departamentos': list(Departamento.objects.all()),
                'usuario': request.usuario,
            }
            
        else:
            # Para suporte: mostrar o dashboard completo
            context = _get_dashboard_context(request, page=page)
            context['usuario'] = request.usuario
        
        # ✅ CORREÇÃO CRÍTICA: Buscar notificações de forma correta para ambos os tipos
        try:
            notificacoes = Notificacao.objects.filter(
                usuario=request.usuario
            ).order_by('-criado_em')[:10]
            
            notificacoes_nao_lidas_count = Notificacao.objects.filter(
                usuario=request.usuario,
                lida=False
            ).count()
            
            context.update({
                'notificacoes': notificacoes,
                'notificacoes_nao_lidas_count': notificacoes_nao_lidas_count,
            })
            
            logger.info(f"Notificações carregadas: {notificacoes.count()} total, {notificacoes_nao_lidas_count} não lidas")
            
        except Exception as e:
            logger.error(f"Erro ao buscar notificações: {str(e)}")
            context.update({
                'notificacoes': [],
                'notificacoes_nao_lidas_count': 0,
            })
        
        logger.info(f"Dashboard carregado para {request.usuario.username} (tipo: {request.usuario.tipo_usuario})")
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {str(e)}")
        # Contexto de fallback em caso de erro
        return render(request, 'dashboard.html', {
            'total_chamados': 0,
            'pendentes_count': 0,
            'solucionados_count': 0,
            'urgentes_count': 0,
            'chamados_recentes': [],
            'chamados_paginados': [],
            'porcentagem_pendentes': 0,
            'filtros_ativos': {},
            'departamentos': [],
            'usuario': request.usuario,
            'notificacoes': [],
            'notificacoes_nao_lidas_count': 0,
        })

# ✅ CORREÇÃO: View todos_chamados corrigida para passar request
@usuario_required
@require_http_methods(["GET"])
def todos_chamados(request):
    """Página para listar todos os chamados (apenas para suporte)"""
    if request.usuario.tipo_usuario != 'suporte':
        logger.warning(f"Tentativa de acesso a todos_chamados por não-suporte: {request.usuario.username}")
        return HttpResponseForbidden("Apenas usuários de suporte podem acessar esta página.")
    
    # ✅ CORREÇÃO: Reutiliza a lógica do dashboard COM FILTROS
    page = request.GET.get('page', 1)
    context = _get_dashboard_context(request, page=page)
    context['usuario'] = request.usuario
    
    return render(request, 'todos_chamados.html', context)

@usuario_required
@require_http_methods(["GET", "POST"])
@rate_limit(max_requests=50, window=3600)
def sistema_chamados(request):
    """View unificada para criação de chamados (página 'Novo Chamado')"""
    criar_departamentos_iniciais()
    departamentos = Departamento.objects.all()
    
    if request.method == 'POST':
        return criar_chamado_api(request)
    
    # Renderiza a página de formulário
    return render(request, 'initial.html', {
        'departamentos': departamentos,
        'usuario': request.usuario
    })

@usuario_required
@require_http_methods(["POST"])
@rate_limit(max_requests=20, window=3600)
def criar_chamado_api(request):
    """API para criar chamado via AJAX/JSON com segurança - CORRIGIDA"""
    try:
        # ✅ CORREÇÃO: Verificar se é requisição AJAX ou form tradicional
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if request.content_type == 'application/json':
            try:
                # Limitar tamanho do body JSON
                if len(request.body) > 10000:  # 10KB max
                    return JsonResponse({
                        'success': False,
                        'message': 'Payload muito grande'
                    }, status=413)
                    
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON inválido recebido de {request.usuario.username}: {e}")
                return JsonResponse({
                    'success': False,
                    'message': 'Dados inválidos'
                }, status=400)
        else:
            data = request.POST
        
        # ✅ CORREÇÃO: Sanitizar e validar dados de forma mais robusta
        titulo = security.sanitize_input(data.get('titulo', '').strip(), max_length=200)
        descricao = security.sanitize_input(data.get('descricao', '').strip(), max_length=1000)
        departamento_id = data.get('departamento')
        localizacao = data.get('localizacao', 'presencial')
        modalidade_presencial = localizacao == 'presencial'
        
        logger.info(f"Tentativa de criar chamado: {titulo} - Dept: {departamento_id} - Local: {localizacao}")
        
        # ✅ CORREÇÃO: Validações mais detalhadas
        if not titulo:
            return JsonResponse({
                'success': False,
                'message': 'Título é obrigatório!'
            }, status=400)
        
        if not descricao:
            return JsonResponse({
                'success': False,
                'message': 'Descrição é obrigatória!'
            }, status=400)
        
        if not departamento_id:
            return JsonResponse({
                'success': False,
                'message': 'Departamento é obrigatório!'
            }, status=400)
        
        if len(titulo) < 5:
            return JsonResponse({
                'success': False,
                'message': 'Título muito curto (mínimo 5 caracteres)'
            }, status=400)
        
        if len(descricao) < 10:
            return JsonResponse({
                'success': False,
                'message': 'Descrição muito curta (mínimo 10 caracteres)'
            }, status=400)
        
        try:
            departamento = Departamento.objects.get(id_departamento=departamento_id)
        except (Departamento.DoesNotExist, ValueError) as e:
            logger.error(f"Departamento não encontrado: {departamento_id} - {e}")
            return JsonResponse({
                'success': False,
                'message': 'Departamento selecionado não encontrado!'
            }, status=400)
        
        # ✅ CORREÇÃO: Criar chamado com tratamento de erro específico
        try:
            chamado = Chamado.objects.create(
                titulo=titulo,
                descricao=descricao,
                nome_solicitante=request.usuario.username,
                departamento=departamento,
                modalidade_presencial=modalidade_presencial,
                status='em_andamento',
                usuario=request.usuario
            )
            
            logger.info(f"Chamado criado com sucesso: {chamado.id_legivel} por {request.usuario.username}")
            
        except Exception as e:
            logger.error(f"Erro ao criar chamado no banco: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Erro ao salvar chamado no banco de dados'
            }, status=500)
        
        # ✅ CORREÇÃO: Criar primeira mensagem com tratamento de erro
        try:
            criar_interacoes_iniciais(chamado, request.usuario.username, departamento, modalidade_presencial)
        except Exception as e:
            logger.error(f"Erro ao criar interações iniciais: {str(e)}")
            # Não falha o chamado por erro nas interações
        
        # ✅ CORREÇÃO CRÍTICA: Agendar verificações de forma correta
        try:
            # ✅ CORREÇÃO: Agendar apenas UMA verificação após 10 minutos
            verificar_chamado_apos_10_minutos(chamado.id_chamado)
            logger.info(f"Verificação agendada para chamado {chamado.id_legivel} após 10 minutos")
        except Exception as e:
            logger.error(f"Erro ao agendar verificações: {str(e)}")
            # Não falha o chamado por erro no agendamento
        
        # ✅ CORREÇÃO: Resposta de sucesso detalhada
        response_data = {
            'success': True,
            'message': 'Chamado criado com sucesso!',
            'chamado_id': str(chamado.id_chamado),
            'chamado_legivel': chamado.id_legivel,
            'nome_solicitante': request.usuario.username,
            'departamento': departamento.nome,
            'titulo': titulo,
            'modalidade': 'Presencial' if modalidade_presencial else 'Home Office',
            'status': chamado.get_status_display(),
            'urgencia': chamado.get_urgencia_display(),
            'sequencia_ativa': True,
            'tipo_usuario': request.usuario.tipo_usuario  # ✅ Adicionar tipo de usuário
        }
        
        logger.info(f"Resposta enviada para criação de chamado: {chamado.id_legivel}")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Erro crítico ao criar chamado via API: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor. Tente novamente.'
        }, status=500)

def criar_interacoes_iniciais(chamado, nome_solicitante, departamento, modalidade_presencial):
    """✅ CORREÇÃO CRÍTICA: Cria APENAS a primeira mensagem do bot e notifica suportes SEPARADAMENTE"""
    try:
        # ✅ CORREÇÃO: Buscar apenas a PRIMEIRA mensagem da sequência
        sequencia = bot_dialogos.get_sequencia_inicial_completa(
            chamado=chamado,
            nome_solicitante=nome_solicitante,
            departamento=departamento,
            modalidade_presencial=modalidade_presencial
        )
        
        if sequencia:
            # ✅ CORREÇÃO CRÍTICA: APENAS a primeira mensagem vai para o chat do chamado
            primeira_interacao = sequencia[0]
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='bot',
                mensagem=primeira_interacao['mensagem'],
                acao_bot=primeira_interacao.get('acao_bot', 'inicio')
            )
            logger.info(f"✅ Interação inicial criada para chamado {chamado.id_legivel}: {primeira_interacao['mensagem'][:50]}...")
            
            # ✅ CORREÇÃO: NOTIFICAR USUÁRIOS DE SUPORTE VIA MODEL SEPARADO
            notificar_suportes_novo_chamado(chamado)
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar interações iniciais: {str(e)}")
        # Cria uma mensagem padrão em caso de erro
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem="Olá! Recebi seu chamado e já estou trabalhando para ajudá-lo.",
            acao_bot='inicio'
        )

def notificar_suportes_novo_chamado(chamado):
    """✅ CORREÇÃO: Notifica suportes E também o usuário colaborador"""
    try:
        # 1. Notificar todos os usuários de suporte
        usuarios_suporte = Usuario.objects.filter(tipo_usuario='suporte')
        
        for usuario_suporte in usuarios_suporte:
            Notificacao.objects.create(
                usuario=usuario_suporte,
                chamado=chamado,
                mensagem=f"🚨 **NOVO CHAMADO CRIADO**\n📝 {chamado.titulo}\n👤 {chamado.nome_solicitante}\n🏢 {chamado.departamento.nome}\n🆔 {chamado.id_legivel}",
                tipo='novo_chamado'
            )
        
        # ✅ CORREÇÃO CRÍTICA: 2. Também notificar o PRÓPRIO USUÁRIO COLABORADOR
        Notificacao.objects.create(
            usuario=chamado.usuario,  # O próprio criador do chamado
            chamado=chamado,
            mensagem=f"✅ **SEU CHAMADO FOI CRIADO!**\n📝 {chamado.titulo}\n🏢 {chamado.departamento.nome}\n🆔 {chamado.id_legivel}\n\nAguarde enquanto nossa equipe entra em contato.",
            tipo='meu_chamado'
        )
        
        logger.info(f"✅ Notificações enviadas para {usuarios_suporte.count()} suportes e para o usuário {chamado.usuario.username}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao notificar suportes e usuário: {str(e)}")

def verificar_chamado_apos_10_minutos(id_chamado):
    """✅ CORREÇÃO CRÍTICA: Verifica se o chamado foi atendido após 10 minutos - SEM DUPLICAÇÃO"""
    def check_chamado():
        logger.info(f"⏰ Iniciando verificação de 10min para chamado {id_chamado}")
        time.sleep(600)  # 10 minutos
        try:
            chamado = Chamado.objects.get(id_chamado=id_chamado)
            if chamado.status == 'em_andamento':
                # ✅ CORREÇÃO: Verificar se já existe uma mensagem de verificação
                verificacao_existente = InteracaoChamado.objects.filter(
                    chamado=chamado,
                    acao_bot='verificacao_tempo'
                ).exists()
                
                if not verificacao_existente:
                    verificacao = bot_dialogos.get_verificacao_tempo()
                    InteracaoChamado.objects.create(
                        chamado=chamado,
                        remetente='bot',
                        mensagem=verificacao['mensagem'],
                        acao_bot=verificacao['acao_bot']
                    )
                    logger.info(f"✅ Verificação de 10min criada para chamado {chamado.id_legivel}")
                    
                    # ✅ CORREÇÃO: Agendar APENAS UMA verificação adicional após 5 minutos
                    verificar_chamado_apos_5_minutos(id_chamado)
                else:
                    logger.info(f"ℹ️ Verificação de 10min já existe para chamado {chamado.id_legivel}")
            else:
                logger.info(f"ℹ️ Chamado {chamado.id_legivel} já foi resolvido, ignorando verificação")
        except Chamado.DoesNotExist:
            logger.warning(f"❌ Chamado {id_chamado} não encontrado para verificação")
        except Exception as e:
            logger.error(f"❌ Erro na verificação de 10min do chamado {id_chamado}: {str(e)}")
    
    thread = threading.Thread(target=check_chamado)
    thread.daemon = True
    thread.start()

def verificar_chamado_apos_5_minutos(id_chamado):
    """✅ CORREÇÃO: Verificação adicional após 5 minutos da primeira verificação - SEM DUPLICAÇÃO"""
    def check_chamado():
        logger.info(f"⏰ Iniciando verificação de 5min adicional para chamado {id_chamado}")
        time.sleep(300)  # 5 minutos
        try:
            chamado = Chamado.objects.get(id_chamado=id_chamado)
            if chamado.status == 'em_andamento':
                # ✅ CORREÇÃO: Verificar se já existe uma mensagem de verificação urgente
                verificacao_urgente_existente = InteracaoChamado.objects.filter(
                    chamado=chamado,
                    acao_bot='verificacao_urgente'
                ).exists()
                
                if not verificacao_urgente_existente:
                    verificacao_urgente = bot_dialogos.get_verificacao_urgente()
                    InteracaoChamado.objects.create(
                        chamado=chamado,
                        remetente='bot',
                        mensagem=verificacao_urgente['mensagem'],
                        acao_bot=verificacao_urgente['acao_bot']
                    )
                    logger.info(f"✅ Verificação urgente criada para chamado {chamado.id_legivel}")
                else:
                    logger.info(f"ℹ️ Verificação urgente já existe para chamado {chamado.id_legivel}")
            else:
                logger.info(f"ℹ️ Chamado {chamado.id_legivel} já foi resolvido, ignorando verificação urgente")
        except Chamado.DoesNotExist:
            logger.warning(f"❌ Chamado {id_chamado} não encontrado para verificação urgente")
        except Exception as e:
            logger.error(f"❌ Erro na verificação urgente do chamado {id_chamado}: {str(e)}")
    
    thread = threading.Thread(target=check_chamado)
    thread.daemon = True
    thread.start()

# === SISTEMA DE NOTIFICAÇÕES CORRIGIDO ===
@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=120, window=3600)
def verificar_notificacoes(request):
    """✅ API CORRIGIDA: Verificar notificações para COLABORADORES E SUPORTE - ATUALIZADO: 45 SEGUNDOS"""
    try:
        # ✅ CORREÇÃO: Lógica diferente para colaboradores vs suporte
        if request.usuario.tipo_usuario == 'colaborador':
            # COLABORADOR: Ver apenas notificações dos SEUS chamados
            notificacoes_nao_lidas = Notificacao.objects.filter(
                chamado__usuario=request.usuario,  # ✅ APENAS chamados do usuário
                lida=False
            ).order_by('-criado_em')
            
            # Buscar notificações recentes do usuário
            notificacoes_recentes = Notificacao.objects.filter(
                chamado__usuario=request.usuario
            ).order_by('-criado_em')[:10]
            
        else:
            # SUPORTE: Ver todas as notificações (comportamento original)
            notificacoes_nao_lidas = Notificacao.objects.filter(
                usuario=request.usuario,
                lida=False
            ).order_by('-criado_em')
            
            notificacoes_recentes = Notificacao.objects.filter(
                usuario=request.usuario
            ).order_by('-criado_em')[:10]
        
        notificacoes_data = []
        for notificacao in notificacoes_recentes:
            hora_local = timezone.localtime(notificacao.criado_em)
            notificacoes_data.append({
                'id': str(notificacao.id_notificacao),
                'mensagem': notificacao.mensagem,
                'chamado_id': str(notificacao.chamado.id_chamado) if notificacao.chamado else None,
                'chamado_legivel': notificacao.chamado.id_legivel if notificacao.chamado else 'N/A',
                'hora': hora_local.strftime('%H:%M'),
                'data_completa': hora_local.strftime('%d/%m/%Y %H:%M'),
                'tipo': notificacao.tipo,
                'lida': notificacao.lida,
                'timestamp': notificacao.criado_em.timestamp()
            })
        
        return JsonResponse({
            'success': True,
            'notificacoes': notificacoes_data,
            'total_nao_lidas': notificacoes_nao_lidas.count(),
            'ultima_verificacao': timezone.now().timestamp(),
            'tipo_usuario': request.usuario.tipo_usuario,
            'intervalo_verificacao': 45  # ✅ ATUALIZADO: 45 segundos
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar notificações: {str(e)}")
        return JsonResponse({
            'success': False,
            'notificacoes': [],
            'total_nao_lidas': 0,
            'message': 'Erro ao carregar notificações'
        })

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=50, window=3600)
def marcar_todas_notificacoes_lidas(request):
    """✅ API: Marcar TODAS as notificações como lidas - APENAS SUPORTE"""
    try:
        # ✅ CORREÇÃO: COLABORADORES NÃO PODEM marcar notificações como lidas
        if request.usuario.tipo_usuario == 'colaborador':
            logger.warning(f"🚫 COLABORADOR tentou marcar todas notificações como lidas: {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Colaboradores não têm permissão para marcar notificações como lidas.'
            }, status=403)
        
        notificacoes_nao_lidas = Notificacao.objects.filter(
            usuario=request.usuario,
            lida=False
        )
        
        count = notificacoes_nao_lidas.update(lida=True)
        
        logger.info(f"Todas as notificações ({count}) marcadas como lidas por {request.usuario.username} (SUPORTE)")
        
        return JsonResponse({
            'success': True,
            'message': f'{count} notificações marcadas como lidas',
            'total_marcadas': count
        })
        
    except Exception as e:
        logger.error(f"Erro ao marcar todas notificações como lidas: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro ao marcar notificações como lidas'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=50, window=3600)
def limpar_notificacoes(request):
    """✅ API: Limpar/Deletar notificações antigas - APENAS SUPORTE"""
    try:
        # ✅ CORREÇÃO: COLABORADORES NÃO PODEM limpar notificações
        if request.usuario.tipo_usuario == 'colaborador':
            logger.warning(f"🚫 COLABORADOR tentou limpar notificações: {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Colaboradores não têm permissão para limpar notificações.'
            }, status=403)
        
        # Manter apenas as últimas 20 notificações
        notificacoes_para_manter = Notificacao.objects.filter(
            usuario=request.usuario
        ).order_by('-criado_em')[:20]
        
        ids_para_manter = [n.id_notificacao for n in notificacoes_para_manter]
        
        # Deletar notificações antigas
        notificacoes_deletadas = Notificacao.objects.filter(
            usuario=request.usuario
        ).exclude(id_notificacao__in=ids_para_manter).delete()
        
        count = notificacoes_deletadas[0] if notificacoes_deletadas else 0
        
        logger.info(f"{count} notificações antigas removidas por {request.usuario.username} (SUPORTE)")
        
        return JsonResponse({
            'success': True,
            'message': f'{count} notificações antigas removidas',
            'total_removidas': count
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar notificações: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro ao limpar notificações'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=50, window=3600)
def marcar_notificacao_como_lida(request, id_notificacao):
    """✅ FUNÇÃO CRÍTICA CORRIGIDA: Marcar notificação como lida com PERMISSÕES RESTRITAS"""
    try:
        print(f"🔔 Tentando marcar notificação {id_notificacao} como lida para usuário {request.usuario.username} (tipo: {request.usuario.tipo_usuario})")
        
        # ✅ CORREÇÃO CRÍTICA: COLABORADORES NÃO PODEM marcar notificações como lidas
        if request.usuario.tipo_usuario == 'colaborador':
            logger.warning(f"🚫 COLABORADOR tentou marcar notificação como lida: {request.usuario.username} -> {id_notificacao}")
            return JsonResponse({
                'success': False,
                'message': 'Colaboradores não têm permissão para marcar notificações como lidas. Apenas o suporte pode gerenciar notificações.'
            }, status=403)
        
        # ✅ APENAS SUPORTE pode marcar notificações como lidas
        notificacao = Notificacao.objects.get(
            id_notificacao=id_notificacao,
            usuario=request.usuario  # ✅ Apenas notificações do próprio usuário de suporte
        )
        
        # Marcar como lida
        notificacao.lida = True
        notificacao.save()
        
        logger.info(f"✅ Notificação {id_notificacao} marcada como lida por {request.usuario.username} (SUPORTE)")
        
        return JsonResponse({
            'success': True,
            'message': 'Notificação marcada como lida',
            'notificacao_id': str(id_notificacao),
            'tipo_usuario': request.usuario.tipo_usuario
        })
        
    except Notificacao.DoesNotExist:
        logger.warning(f"🚫 Tentativa de marcar notificação inexistente: {id_notificacao} por {request.usuario.username}")
        return JsonResponse({
            'success': False,
            'message': 'Notificação não encontrada'
        }, status=404)
    except Exception as e:
        logger.error(f"❌ Erro ao marcar notificação como lida: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=100, window=3600)
def obter_notificacoes_usuario(request):
    """✅ FUNÇÃO CRÍTICA: Obter todas as notificações do usuário (com paginação)"""
    try:
        # Parâmetros de paginação
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        
        # Buscar notificações do usuário
        notificacoes_query = Notificacao.objects.filter(
            usuario=request.usuario
        ).order_by('-criado_em')
        
        # Paginação
        paginator = Paginator(notificacoes_query, limit)
        
        try:
            notificacoes_pagina = paginator.page(page)
        except PageNotAnInteger:
            notificacoes_pagina = paginator.page(1)
        except EmptyPage:
            notificacoes_pagina = paginator.page(paginator.num_pages)
        
        # Preparar dados das notificações
        notificacoes_data = []
        for notificacao in notificacoes_pagina:
            hora_local = timezone.localtime(notificacao.criado_em)
            notificacoes_data.append({
                'id': str(notificacao.id_notificacao),
                'mensagem': notificacao.mensagem,
                'chamado_id': str(notificacao.chamado.id_chamado) if notificacao.chamado else None,
                'chamado_legivel': notificacao.chamado.id_legivel if notificacao.chamado else 'N/A',
                'hora': hora_local.strftime('%H:%M'),
                'data_completa': hora_local.strftime('%d/%m/%Y %H:%M'),
                'tipo': notificacao.tipo,
                'lida': notificacao.lida,
                'timestamp': notificacao.criado_em.timestamp(),
                'pode_marcar_lida': request.usuario.tipo_usuario == 'suporte'  # ✅ Flag para frontend
            })
        
        # Estatísticas
        total_nao_lidas = Notificacao.objects.filter(
            usuario=request.usuario,
            lida=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'notificacoes': notificacoes_data,
            'pagina_atual': page,
            'total_paginas': paginator.num_pages,
            'total_notificacoes': notificacoes_query.count(),
            'total_nao_lidas': total_nao_lidas,
            'limite_por_pagina': limit,
            'permite_gerenciar_notificacoes': request.usuario.tipo_usuario == 'suporte'
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter notificações do usuário: {str(e)}")
        return JsonResponse({
            'success': False,
            'notificacoes': [],
            'total_nao_lidas': 0,
            'message': 'Erro ao carregar notificações'
        }, status=500)

# === FUNÇÕES DE SUPORTE QUE ESTAVAM FALTANDO ===

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=20, window=3600)
def intermediar_chat_bot(request, id_chamado):
    """API para o suporte intermediar o chat com o bot"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        if request.usuario.tipo_usuario != 'suporte':
            return JsonResponse({
                'success': False,
                'message': 'Apenas usuários de suporte podem intermediar o chat.'
            }, status=403)
        
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # Verificar se já existe um suporte responsável
        if chamado.suporte_responsavel and chamado.suporte_responsavel != request.usuario:
            return JsonResponse({
                'success': False,
                'message': f'Este chamado já está sendo atendido por {chamado.suporte_responsavel.username}.'
            }, status=403)
        
        # Atualizar o chamado com o suporte responsável
        chamado.suporte_responsavel = request.usuario
        chamado.controle_chat_suporte = True
        chamado.visualizado_suporte = True
        chamado.save()
        
        # Criar mensagem informando que o suporte está intermediando
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='suporte',
            mensagem=f"🛠️ **{request.usuario.username} está agora intermediando este chat**\nEstou aqui para ajudar no atendimento e garantir que tudo seja resolvido da melhor forma possível.",
            suporte_responsavel=request.usuario
        )
        
        # Criar mensagem do bot confirmando a intermediação
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem="🤖 **Modo de intermediação ativado**\nA partir de agora, o suporte técnico está acompanhando nossa conversa e pode intervir quando necessário para agilizar a solução.",
            acao_bot='intermediacao_ativa'
        )
        
        logger.info(f"Suporte {request.usuario.username} intermediando chat {id_chamado}")
        
        return JsonResponse({
            'success': True,
            'message': 'Chat intermediado com sucesso!',
            'suporte_responsavel': request.usuario.username
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao intermediar chat: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=20, window=3600)
def trocar_status_chamado(request, id_chamado):
    """API para trocar status do chamado"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # Verificar permissões
        if request.usuario.tipo_usuario != 'suporte' and chamado.usuario != request.usuario:
            logger.warning(f"Tentativa de alterar status não autorizada: {request.usuario.username} -> {id_chamado}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado.'
            }, status=403)
        
        # Ler dados da requisição
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        novo_status = data.get('status')
        observacao = security.sanitize_input(data.get('observacao', ''), max_length=200)
        
        if not novo_status:
            return JsonResponse({
                'success': False,
                'message': 'Status é obrigatório.'
            }, status=400)
        
        if novo_status not in dict(Chamado.STATUS_CHOICES):
            return JsonResponse({
                'success': False,
                'message': 'Status inválido.'
            }, status=400)
        
        # Salvar status anterior para mensagem
        status_anterior = chamado.get_status_display()
        
        # Atualizar chamado
        chamado.status = novo_status
        if novo_status == 'resolvido':
            chamado.data_resolucao = timezone.now()
        chamado.save()
        
        # Criar mensagem de atualização
        mensagem_status = f"📊 **Status alterado:** {status_anterior} → {chamado.get_status_display()}"
        if observacao:
            mensagem_status += f"\n💬 **Observação:** {observacao}"
        
        if request.usuario.tipo_usuario == 'suporte':
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='suporte',
                mensagem=mensagem_status,
                suporte_responsavel=request.usuario
            )
        else:
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='usuario',
                mensagem=mensagem_status
            )
        
        # Se foi resolvido pelo suporte, adicionar mensagem do bot de finalização
        if novo_status == 'resolvido' and request.usuario.tipo_usuario == 'suporte':
            finalizacao = bot_dialogos.get_finalizacao_suporte()
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='bot',
                mensagem=finalizacao['mensagem'],
                acao_bot=finalizacao['acao_bot']
            )
            
            # ✅ CORREÇÃO: Adicionar mensagem final de agradecimento
            finalizacao_completa = bot_dialogos.get_mensagem_finalizacao_completa()
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='bot',
                mensagem=finalizacao_completa['mensagem'],
                acao_bot=finalizacao_completa['acao_bot']
            )
        
        logger.info(f"Status do chamado {id_chamado} alterado para {novo_status} por {request.usuario.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Status atualizado com sucesso!',
            'novo_status': chamado.get_status_display(),
            'novo_status_value': novo_status
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao trocar status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=20, window=3600)
def marcar_chamado_visualizado(request, id_chamado):
    """API para marcar chamado como visualizado pelo suporte"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        if request.usuario.tipo_usuario != 'suporte':
            return JsonResponse({
                'success': False,
                'message': 'Apenas usuários de suporte podem marcar chamados como visualizados.'
            }, status=403)
        
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        chamado.visualizado_suporte = True
        chamado.save()
        
        logger.info(f"Chamado {id_chamado} marcado como visualizado por {request.usuario.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Chamado marcado como visualizado!'
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao marcar chamado como visualizado: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=20, window=3600)
def assumir_controle_chat(request, id_chamado):
    """API para o suporte assumir controle do chat"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        if request.usuario.tipo_usuario != 'suporte':
            return JsonResponse({
                'success': False,
                'message': 'Apenas usuários de suporte podem assumir controle do chat.'
            }, status=403)
        
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # Atualizar o chamado com o suporte responsável e controle
        chamado.suporte_responsavel = request.usuario
        chamado.controle_chat_suporte = True
        chamado.visualizado_suporte = True  # Marcar como visualizado também
        chamado.save()
        
        # Criar mensagem informando que o suporte assumiu o controle
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='suporte',
            mensagem=f"👨‍💼 **{request.usuario.username} assumiu o controle do chat**\nA partir de agora, você está em contato direto com o suporte técnico.",
            suporte_responsavel=request.usuario
        )
        
        logger.info(f"Suporte {request.usuario.username} assumiu controle do chat {id_chamado}")
        
        return JsonResponse({
            'success': True,
            'message': 'Controle do chat assumido com sucesso!',
            'suporte_responsavel': request.usuario.username
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao assumir controle do chat: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=20, window=3600)
def enviar_mensagem_suporte(request, id_chamado):
    """API para o suporte enviar mensagem no chat (quando tem controle)"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        if request.usuario.tipo_usuario != 'suporte':
            return JsonResponse({
                'success': False,
                'message': 'Apenas usuários de suporte podem enviar mensagens diretas.'
            }, status=403)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        mensagem = security.sanitize_input(data.get('mensagem', '').strip(), max_length=500)
        
        if not mensagem:
            return JsonResponse({
                'success': False,
                'message': 'Mensagem não pode estar vazia'
            }, status=400)
        
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # Verificar se o suporte tem controle do chat ou é o responsável
        if not chamado.controle_chat_suporte and chamado.suporte_responsavel != request.usuario:
            return JsonResponse({
                'success': False,
                'message': 'Você precisa assumir o controle do chat antes de enviar mensagens.'
            }, status=403)
        
        # Criar mensagem do suporte
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='suporte',
            mensagem=mensagem,
            suporte_responsavel=request.usuario
        )
        
        logger.info(f"Mensagem do suporte enviada no chamado {id_chamado} por {request.usuario.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Mensagem enviada com sucesso!'
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem do suporte: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@require_http_methods(["GET"])
@usuario_required
def api_dados_grafico(request):
    """API: Retorna dados atualizados para o gráfico"""
    try:
        if request.usuario.tipo_usuario != 'suporte':
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado'
            }, status=403)
        
        # Dados reais por departamento
        departamentos_data = []
        departamentos = Departamento.objects.all()
        
        for dept in departamentos:
            quantidade = Chamado.objects.filter(departamento=dept).count()
            departamentos_data.append({
                'nome': dept.nome,
                'quantidade': quantidade
            })
        
        # Dados de status para gráfico de pizza
        status_data = {
            'em_andamento': Chamado.objects.filter(status='em_andamento').count(),
            'resolvido': Chamado.objects.filter(status='resolvido').count(),
            'aguardando': Chamado.objects.filter(status='aguardando').count()
        }
        
        # Estatísticas gerais
        estatisticas = {
            'total_chamados': Chamado.objects.count(),
            'pendentes_count': Chamado.objects.filter(status='em_andamento').count(),
            'solucionados_count': Chamado.objects.filter(status='resolvido').count(),
            'urgentes_count': Chamado.objects.filter(urgencia='urgente', status='em_andamento').count(),
            'novos_hoje': Chamado.objects.filter(
                criado_em__date=timezone.now().date()
            ).count()
        }
        
        return JsonResponse({
            'success': True,
            'departamentos_data': departamentos_data,
            'status_data': status_data,
            'estatisticas': estatisticas,
            'atualizado_em': timezone.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Erro em api_dados_grafico: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

# === VIEWS EXISTENTES (MANTIDAS PARA COMPATIBILIDADE) ===

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=10, window=3600)
def confirmar_atendimento(request, id_chamado):
    """API para o suporte confirmar que atendeu o chamado - ATUALIZADA COM MENSAGEM FINAL"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        if request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Tentativa de confirmar atendimento sem permissão: {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Apenas usuários de suporte podem confirmar atendimentos.'
            }, status=403)
        
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        chamado.status = 'resolvido'
        chamado.data_resolucao = timezone.now()
        chamado.save()
        
        # ✅ CORREÇÃO: Usar a mensagem completa de finalização
        finalizacao = bot_dialogos.get_finalizacao_suporte()
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=finalizacao['mensagem'],
            acao_bot=finalizacao['acao_bot']
        )
        
        # ✅ CORREÇÃO ADICIONAL: Adicionar mensagem de agradecimento final
        finalizacao_completa = bot_dialogos.get_mensagem_finalizacao_completa()
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=finalizacao_completa['mensagem'],
            acao_bot=finalizacao_completa['acao_bot']
        )
        
        logger.info(f"Chamado {id_chamado} marcado como resolvido por {request.usuario.username}")
        return JsonResponse({
            'success': True,
            'message': 'Chamado marcado como resolvido com sucesso!'
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao confirmar atendimento: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=10, window=3600)
def usuario_confirmar_resolucao(request, id_chamado):
    """API para o usuário confirmar que o problema foi resolvido - ATUALIZADA COM MENSAGEM FINAL"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        if chamado.usuario != request.usuario:
            logger.warning(f"Tentativa de confirmar resolução de chamado alheio: {request.usuario.username} -> {id_chamado}")
            return JsonResponse({
                'success': False,
                'message': 'Você só pode confirmar resolução dos seus próprios chamados.'
            }, status=403)
        
        chamado.status = 'resolvido'
        chamado.data_resolucao = timezone.now()
        chamado.save()
        
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='usuario',
            mensagem="✅ Confirmo que meu problema foi resolvido!"
        )
        
        # ✅ CORREÇÃO: Usar a mensagem completa de finalização
        finalizacao = bot_dialogos.get_finalizacao_usuario()
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=finalizacao['mensagem'],
            acao_bot=finalizacao['acao_bot']
        )
        
        # ✅ CORREÇÃO ADICIONAL: Adicionar mensagem de agradecimento final
        finalizacao_completa = bot_dialogos.get_mensagem_finalizacao_completa()
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=finalizacao_completa['mensagem'],
            acao_bot=finalizacao_completa['acao_bot']
        )
        
        logger.info(f"Chamado {id_chamado} finalizado pelo usuário {request.usuario.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Chamado finalizado com sucesso!'
        })
            
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao confirmar resolução: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
@usuario_required
@rate_limit(max_requests=30, window=3600)
def proxima_mensagem_bot(request, id_chamado):
    """API para adicionar próxima mensagem na sequência (UMA DE CADA VEZ)"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO CRÍTICA: Permitir que COLABORADORES acessem seus próprios chats
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username} (tipo: {request.usuario.tipo_usuario})")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        # Contar quantas mensagens do bot já existem
        mensagens_count = InteracaoChamado.objects.filter(
            chamado=chamado, 
            remetente='bot'
        ).count()
        
        # Pegar a sequência completa da biblioteca
        sequencia = bot_dialogos.get_sequencia_inicial_completa(
            chamado=chamado,
            nome_solicitante=chamado.nome_solicitante,
            departamento=chamado.departamento,
            modalidade_presencial=chamado.modalidade_presencial
        )
        
        # Verificar se já completou todas as mensagens
        if mensagens_count >= len(sequencia):
            return JsonResponse({
                'success': True,
                'completo': True,
                'message': 'Sequência completa'
            })
        
        # Pegar próxima mensagem da biblioteca
        proxima_msg = sequencia[mensagens_count]
        
        # Criar a mensagem no banco
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=proxima_msg['mensagem'],
            acao_bot=proxima_msg.get('acao_bot', 'mensagem')
        )
        
        # Verificar se é a última mensagem
        completo = (mensagens_count + 1) >= len(sequencia)
        
        return JsonResponse({
            'success': True,
            'mensagem': proxima_msg['mensagem'],
            'indice': mensagens_count + 1,
            'total': len(sequencia),
            'completo': completo
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em proxima_mensagem_bot: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=60, window=3600)
def carregar_mensagens_chat(request, id_chamado):
    """API para carregar todas as mensagens do chat - CORRIGIDA PARA COLABORADORES"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO CRÍTICA: Permitir que COLABORADORES acessem seus próprios chats
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username} (tipo: {request.usuario.tipo_usuario})")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        # Buscar TODAS as interações do chat
        interacoes = InteracaoChamado.objects.filter(chamado=chamado).order_by('criado_em')
        
        mensagens = []
        for interacao in interacoes:
            hora_local = timezone.localtime(interacao.criado_em)
            mensagens.append({
                'id': str(interacao.id_interacao),
                'remetente': interacao.remetente,
                'mensagem': interacao.mensagem,
                'hora': hora_local.strftime('%H:%M'),
                'acao_bot': interacao.acao_bot,
                'suporte_responsavel': interacao.suporte_responsavel.username if interacao.suporte_responsavel else None
            })
        
        return JsonResponse({
            'success': True,
            'chamado_id': str(chamado.id_chamado),
            'chamado_legivel': chamado.id_legivel,
            'titulo': chamado.titulo,
            'status': chamado.get_status_display(),
            'urgencia': chamado.get_urgencia_display(),
            'controle_suporte': chamado.controle_chat_suporte,
            'suporte_responsavel': chamado.suporte_responsavel.username if chamado.suporte_responsavel else None,
            'mensagens': mensagens
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em carregar_mensagens_chat: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=30, window=3600)
def enviar_mensagem(request, id_chamado):
    """API para enviar mensagens no chat do chamado com segurança"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        # ✅ CORREÇÃO: Verificar se o chamado existe ANTES de processar
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO CRÍTICA: Verificar se o chamado já está resolvido
        if chamado.status == 'resolvido':
            logger.info(f"Tentativa de enviar mensagem em chamado resolvido: {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Este chamado já foi resolvido e não aceita novas mensagens.'
            }, status=400)
        
        if request.content_type == 'application/json':
            if len(request.body) > 5000:
                return JsonResponse({
                    'success': False,
                    'message': 'Mensagem muito longa'
                }, status=413)
            data = json.loads(request.body)
        else:
            data = request.POST
            
        mensagem = security.sanitize_input(data.get('mensagem', '').strip(), max_length=500)
        
        if not mensagem:
            return JsonResponse({
                'success': False,
                'message': 'Mensagem não pode estar vazia'
            }, status=400)
        
        if len(mensagem) < 2:
            return JsonResponse({
                'success': False,
                'message': 'Mensagem muito curta'
            }, status=400)
        
        # ✅ CORREÇÃO CRÍTICA: Permitir que COLABORADORES acessem seus próprios chats
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Tentativa de enviar mensagem em chamado alheio: {request.usuario.username} -> {id_chamado}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        resposta_data = None
        intencao_detectada = None
        
        # Se for suporte e tiver controle, enviar como suporte
        if request.usuario.tipo_usuario == 'suporte' and chamado.controle_chat_suporte:
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='suporte',
                mensagem=mensagem,
                suporte_responsavel=request.usuario
            )
            
            logger.info(f"Mensagem do suporte enviada no chamado {id_chamado} por {request.usuario.username}")
            
        else:
            # Caso contrário, enviar como usuário normal
            InteracaoChamado.objects.create(
                chamado=chamado,
                remetente='usuario',
                mensagem=mensagem
            )
            
            # ✅ CORREÇÃO: Resposta do bot apenas para usuários normais - com tratamento de erro
            try:
                resposta_data = bot_dialogos.get_resposta_inteligente(mensagem, chamado, request.usuario)
                
                # ✅ CORREÇÃO: Verificar se a resposta do bot indica resolução
                if resposta_data and resposta_data.get('acao_bot') == 'finalizacao_usuario':
                    # Se for uma finalização, marcar o chamado como resolvido
                    chamado.status = 'resolvido'
                    chamado.data_resolucao = timezone.now()
                    chamado.save()
                    logger.info(f"Chamado {id_chamado} marcado como resolvido via resposta do bot")
                
                InteracaoChamado.objects.create(
                    chamado=chamado,
                    remetente='bot',
                    mensagem=resposta_data['mensagem'],
                    acao_bot=resposta_data['acao_bot']
                )
                
                intencao_detectada = resposta_data.get('intencao_detectada', 'nao_identificada')
                
            except Exception as e:
                logger.error(f"Erro ao gerar resposta do bot: {str(e)}")
                # ✅ CORREÇÃO: Resposta de fallback em caso de erro no bot
                resposta_data = {
                    'mensagem': "🤖 Obrigado pela sua mensagem! Estou processando sua solicitação.",
                    'acao_bot': 'mensagem_fallback',
                    'intencao_detectada': 'nao_identificada'
                }
                
                InteracaoChamado.objects.create(
                    chamado=chamado,
                    remetente='bot',
                    mensagem=resposta_data['mensagem'],
                    acao_bot=resposta_data['acao_bot']
                )
                
                intencao_detectada = 'nao_identificada'
        
        logger.info(f"Mensagem enviada no chamado {id_chamado} por {request.usuario.username}")
        
        # ✅ CORREÇÃO: Preparar resposta baseada no tipo de usuário
        response_data = {
            'success': True,
        }
        
        if request.usuario.tipo_usuario != 'suporte':
            response_data['resposta'] = resposta_data['mensagem'] if resposta_data else None
            response_data['intencao_detectada'] = intencao_detectada
            # ✅ CORREÇÃO: Adicionar flag se o chamado foi resolvido
            response_data['chamado_resolvido'] = chamado.status == 'resolvido'
        
        return JsonResponse(response_data)
        
    except Chamado.DoesNotExist:
        logger.error(f"Chamado não encontrado: {id_chamado}")
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=60, window=3600)
def carregar_notificacoes(request):
    """API para carregar notificações do usuário"""
    try:
        # Buscar notificações do modelo
        notificacoes = Notificacao.objects.filter(
            usuario=request.usuario,
            lida=False
        ).order_by('-criado_em')[:10]
        
        notificacoes_data = []
        for notificacao in notificacoes:
            hora_local = timezone.localtime(notificacao.criado_em)
            notificacoes_data.append({
                'id': str(notificacao.id_notificacao),
                'mensagem': notificacao.mensagem,
                'chamado_id': str(notificacao.chamado.id_chamado),
                'chamado_legivel': notificacao.chamado.id_legivel,
                'hora': hora_local.strftime('%H:%M'),
                'tipo': notificacao.tipo,
                'lida': notificacao.lida
            })
        
        return JsonResponse({
            'success': True,
            'notificacoes': notificacoes_data,
            'total_nao_lidas': notificacoes.count()
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar notificações: {str(e)}")
        return JsonResponse({
            'success': False,
            'notificacoes': [],
            'total_nao_lidas': 0
        })

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=30, window=3600)
def marcar_notificacao_lida(request, id_notificacao):
    """API para marcar notificação como lida"""
    try:
        notificacao = Notificacao.objects.get(
            id_notificacao=id_notificacao,
            usuario=request.usuario
        )
        notificacao.lida = True
        notificacao.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notificação marcada como lida'
        })
        
    except Notificacao.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notificação não encontrada'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao marcar notificação como lida: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@require_http_methods(["GET"])
@usuario_required
def api_info(request):
    """Endpoint para API JSON com informações do sistema"""
    return JsonResponse({
        'message': '🚀 API Projeto AI - Online!',
        'usuario': {
            'username': request.usuario.username,
            'tipo_usuario': request.usuario.tipo_usuario,
        },
        'endpoints': {
            'admin': '/admin/',
            'api_info': '/api/info/',
            'home': '/',
            'dashboard': '/dashboard/',
            'sistema_chamados': '/chamados/',
            'logout': '/logout/',
        }
    })

@require_http_methods(["GET"])
@usuario_required
def detalhes_chamado(request, id_chamado):
    """Página de detalhes do chamado"""
    if not security.validate_uuid(id_chamado):
        return HttpResponseForbidden("ID de chamado inválido")
    
    chamado = get_object_or_404(Chamado, id_chamado=id_chamado)
    
    # ✅ CORREÇÃO: Permitir que COLABORADORES acessem seus próprios chamados
    if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
        logger.warning(f"Tentativa de acesso não autorizado aos detalhes do chamado {id_chamado} por {request.usuario.username}")
        return HttpResponseForbidden("Acesso não autorizado a este chamado.")
    
    # Buscar TODAS as interações do chat
    interacoes = InteracaoChamado.objects.filter(chamado=chamado).order_by('criado_em')
    
    return render(request, 'detalhes_chamado.html', {
        'chamado': chamado,
        'interacoes': interacoes,
        'usuario': request.usuario
    })

@require_http_methods(["GET"])
@usuario_required
def meus_chamados(request):
    """Página para listar os chamados do usuário"""
    criar_departamentos_iniciais()
    departamentos = Departamento.objects.all()
    return render(request, 'initial.html', {
        'departamentos': departamentos,
        'usuario': request.usuario
    })

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=20, window=3600)
def atualizar_status_chamado(request, id_chamado):
    """API para atualizar o status de um chamado"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO: Permitir que COLABORADORES atualizem seus próprios chamados
        if request.usuario.tipo_usuario != 'suporte' and chamado.usuario != request.usuario:
            logger.warning(f"Tentativa de atualizar status não autorizada: {request.usuario.username} -> {id_chamado}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado.'
            }, status=403)
        
        # Verificar o content type para determinar como ler os dados
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        novo_status = data.get('status')
        
        if novo_status not in dict(Chamado.STATUS_CHOICES):
            return JsonResponse({
                'success': False,
                'message': 'Status inválido.'
            }, status=400)
        
        chamado.status = novo_status
        if novo_status == 'resolvido':
            chamado.data_resolucao = timezone.now()
        chamado.save()
        
        InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=f"📊 **Status atualizado:** {chamado.get_status_display()}",
            acao_bot='atualizacao_status'
        )
        
        logger.info(f"Status do chamado {id_chamado} atualizado para {novo_status} por {request.usuario.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Status atualizado com sucesso!',
            'novo_status': chamado.get_status_display()
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=120, window=3600)
def verificar_novas_mensagens(request, id_chamado):
    """API para verificar se há novas mensagens no chat"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO: Permitir que COLABORADORES verifiquem seus próprios chats
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        # Buscar a última mensagem conhecida (se fornecida)
        ultima_mensagem_id = request.GET.get('ultima_mensagem_id')
        
        # Buscar todas as mensagens do chamado
        todas_mensagens = InteracaoChamado.objects.filter(
            chamado=chamado
        ).order_by('criado_em')
        
        # Se não há mensagens, retornar vazio
        if not todas_mensagens.exists():
            return JsonResponse({
                'success': True,
                'novas_mensagens': [],
                'total_novas': 0,
                'ultima_mensagem_id': None
            })
        
        # Nova lógica usando UUID do chamado como referência
        novas_mensagens = todas_mensagens
        ultima_id_encontrada = None
        
        if ultima_mensagem_id:
            try:
                # Buscar a última mensagem conhecida pelo seu ID (se for UUID válido)
                if security.validate_uuid(ultima_mensagem_id):
                    ultima_mensagem_conhecida = InteracaoChamado.objects.filter(
                        id_interacao=ultima_mensagem_id
                    ).first()
                    
                    if ultima_mensagem_conhecida:
                        # Buscar mensagens mais recentes que a última conhecida
                        novas_mensagens = InteracaoChamado.objects.filter(
                            chamado=chamado,
                            criado_em__gt=ultima_mensagem_conhecida.criado_em
                        ).order_by('criado_em')
                    else:
                        # Se não encontrou a mensagem específica, retornar todas
                        novas_mensagens = todas_mensagens
                else:
                    # Se não é UUID, tentar como inteiro (backward compatibility)
                    try:
                        ultima_id_int = int(ultima_mensagem_id)
                        ultima_mensagem_conhecida = InteracaoChamado.objects.filter(
                            id_interacao=ultima_id_int
                        ).first()
                        
                        if ultima_mensagem_conhecida:
                            novas_mensagens = InteracaoChamado.objects.filter(
                                chamado=chamado,
                                criado_em__gt=ultima_mensagem_conhecida.criado_em
                            ).order_by('criado_em')
                        else:
                            novas_mensagens = todas_mensagens
                    except ValueError:
                        # Se não é nem UUID nem inteiro, retornar todas as mensagens
                        novas_mensagens = todas_mensagens
            except Exception as e:
                novas_mensagens = todas_mensagens
        else:
            # Se não há última mensagem ID, retornar todas as mensagens
            novas_mensagens = todas_mensagens
        
        # Preparar dados das mensagens
        mensagens_data = []
        for mensagem in novas_mensagens:
            hora_local = timezone.localtime(mensagem.criado_em)
            mensagens_data.append({
                'id': str(mensagem.id_interacao),
                'remetente': mensagem.remetente,
                'mensagem': mensagem.mensagem,
                'hora': hora_local.strftime('%H:%M'),
                'acao_bot': mensagem.acao_bot,
                'suporte_responsavel': mensagem.suporte_responsavel.username if mensagem.suporte_responsavel else None
            })
            ultima_id_encontrada = str(mensagem.id_interacao)
        
        return JsonResponse({
            'success': True,
            'novas_mensagens': mensagens_data,
            'total_novas': len(mensagens_data),
            'ultima_mensagem_id': ultima_id_encontrada or ultima_mensagem_id
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em verificar_novas_mensagens: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@require_http_methods(["GET"])
@usuario_required
def api_chamados_recentes(request):
    """API para verificar chamados recentes (últimos 5 minutos)"""
    if request.usuario.tipo_usuario != 'suporte':
        return JsonResponse({
            'success': False,
            'message': 'Acesso não autorizado'
        }, status=403)
    
    try:
        # Calcular timestamp de 5 minutos atrás
        cinco_minutos_atras = timezone.now() - timezone.timedelta(minutes=5)
        
        # Contar chamados criados nos últimos 5 minutos
        novos_chamados_count = Chamado.objects.filter(
            criado_em__gte=cinco_minutos_atras
        ).count()
        
        return JsonResponse({
            'success': True,
            'novos_chamados': novos_chamados_count,
            'ultima_verificacao': timezone.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Erro em api_chamados_recentes: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)
    
# === CORREÇÕES CRÍTICAS PARA O PROBLEMA DAS NOTIFICAÇÕES ===
@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=120, window=3600)
def verificar_novas_mensagens_inteligente(request, id_chamado):
    """✅ API INTELIGENTE CORRIGIDA para verificar novas mensagens - CORREÇÃO CRÍTICA"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO: Permitir que COLABORADORES verifiquem seus próprios chats
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        # ✅ CORREÇÃO CRÍTICA: Usar ID da última mensagem visualizada, não timestamp
        ultima_mensagem_visualizada_id = request.GET.get('ultima_visualizada_id')
        
        print(f"🔍 API verificar_novas_mensagens_inteligente - ultima_visualizada_id recebido: {ultima_mensagem_visualizada_id}")
        
        # Buscar TODAS as mensagens do chamado
        todas_mensagens = InteracaoChamado.objects.filter(
            chamado=chamado
        ).order_by('criado_em')
        
        if not todas_mensagens.exists():
            return JsonResponse({
                'success': True,
                'novas_mensagens': [],
                'total_novas': 0,
                'ultima_verificacao': timezone.now().timestamp(),
                'ultima_visualizada_id': None
            })
        
        # ✅ CORREÇÃO CRÍTICA: Filtrar por ID da última mensagem visualizada
        novas_mensagens = todas_mensagens
        if ultima_mensagem_visualizada_id and ultima_mensagem_visualizada_id not in ['undefined', 'null', '']:
            try:
                # Buscar a última mensagem visualizada
                if security.validate_uuid(ultima_mensagem_visualizada_id):
                    ultima_visualizada = InteracaoChamado.objects.filter(
                        id_interacao=ultima_mensagem_visualizada_id
                    ).first()
                    
                    if ultima_visualizada:
                        # ✅ FILTRAR: Apenas mensagens MAIS RECENTES que a última visualizada
                        novas_mensagens = InteracaoChamado.objects.filter(
                            chamado=chamado,
                            criado_em__gt=ultima_visualizada.criado_em
                        ).order_by('criado_em')
                        print(f"✅ Filtro aplicado: {novas_mensagens.count()} mensagens após ID {ultima_mensagem_visualizada_id}")
                    else:
                        # Se não encontrou a mensagem específica, considerar TODAS como não visualizadas
                        print(f"⚠️ Mensagem visualizada não encontrada: {ultima_mensagem_visualizada_id}")
                        novas_mensagens = todas_mensagens
                else:
                    # Se não é UUID válido, considerar TODAS como não visualizadas
                    print(f"⚠️ ID de visualização inválido: {ultima_mensagem_visualizada_id}")
                    novas_mensagens = todas_mensagens
            except Exception as e:
                print(f"⚠️ Erro ao processar última mensagem visualizada, retornando todas: {e}")
                novas_mensagens = todas_mensagens
        else:
            # ✅ Se não há última mensagem visualizada, TODAS são consideradas novas
            print("ℹ️ Nenhum ID de visualização válido fornecido, retornando todas as mensagens")
            novas_mensagens = todas_mensagens
        
        print(f"📨 Novas mensagens NÃO VISUALIZADAS encontradas: {novas_mensagens.count()}")
        
        # ✅ EXCEÇÕES: Não notificar sobre certos tipos de mensagens do bot
        mensagens_filtradas = []
        for mensagem in novas_mensagens:
            # ✅ EXCEÇÃO 1: Não notificar mensagens de "status atualizado" do bot
            if (mensagem.remetente == 'bot' and 
                'status atualizado' in mensagem.mensagem.lower()):
                print(f"🚫 Ignorando mensagem de status atualizado: {mensagem.mensagem[:50]}...")
                continue
            
            # ✅ EXCEÇÃO 2: Não notificar mensagens de "verificação" automática
            if (mensagem.remetente == 'bot' and 
                any(palavra in mensagem.mensagem.lower() for palavra in ['verificando', 'aguardando', 'confirmando'])):
                print(f"🚫 Ignorando mensagem de verificação automática: {mensagem.mensagem[:50]}...")
                continue
            
            # ✅ EXCEÇÃO 3: Não notificar mensagens muito antigas (mais de 1 hora)
            tempo_decorrido = timezone.now() - mensagem.criado_em
            if tempo_decorrido.total_seconds() > 3600:  # 1 hora
                print(f"🚫 Ignorando mensagem muito antiga: {mensagem.mensagem[:50]}...")
                continue
            
            mensagens_filtradas.append(mensagem)
        
        print(f"✅ Mensagens APÓS filtro de exceções: {len(mensagens_filtradas)}")
        
        # Preparar dados das mensagens
        mensagens_data = []
        for mensagem in mensagens_filtradas:
            hora_local = timezone.localtime(mensagem.criado_em)
            mensagens_data.append({
                'id': str(mensagem.id_interacao),
                'remetente': mensagem.remetente,
                'mensagem': mensagem.mensagem,
                'hora': hora_local.strftime('%H:%M'),
                'acao_bot': mensagem.acao_bot,
                'suporte_responsavel': mensagem.suporte_responsavel.username if mensagem.suporte_responsavel else None,
                'timestamp': mensagem.criado_em.timestamp()
            })
        
        # ✅ CORREÇÃO CRÍTICA: Determinar a última mensagem visualizada (para próxima verificação)
        ultima_visualizada_id = None
        if todas_mensagens.exists():
            ultima_mensagem_global = todas_mensagens.last()
            ultima_visualizada_id = str(ultima_mensagem_global.id_interacao)
            print(f"📝 Última mensagem global ID: {ultima_visualizada_id}")
        else:
            ultima_visualizada_id = ultima_mensagem_visualizada_id
        
        # ✅ CORREÇÃO: Garantir que ultima_visualizada_id nunca seja undefined
        if not ultima_visualizada_id:
            ultima_visualizada_id = ultima_mensagem_visualizada_id
        
        return JsonResponse({
            'success': True,
            'novas_mensagens': mensagens_data,
            'total_novas': len(mensagens_data),
            'ultima_verificacao': timezone.now().timestamp(),
            'ultima_visualizada_id': ultima_visualizada_id,  # ✅ CORREÇÃO: Sempre retornar valor válido
            'chamado_status': chamado.status,
            'controle_suporte': chamado.controle_chat_suporte
        })
        
    except Chamado.DoesNotExist:
        print(f"❌ Chamado não encontrado: {id_chamado}")
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em verificar_novas_mensagens_inteligente: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
def marcar_mensagens_visualizadas(request, id_chamado):
    """✅ NOVA API: Marcar mensagens como visualizadas de forma persistente"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO: Permitir que COLABORADORES marquem mensagens como visualizadas
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        # ✅ CORREÇÃO: Usar timestamp em vez de IDs específicos
        timestamp_visualizacao = data.get('timestamp_visualizacao')
        
        if timestamp_visualizacao:
            try:
                # Armazenar na sessão o timestamp da última visualização
                request.session[f'ultima_visualizacao_{id_chamado}'] = float(timestamp_visualizacao)
                request.session.modified = True
                
                logger.info(f"Mensagens do chamado {id_chamado} marcadas como visualizadas por {request.usuario.username} (timestamp: {timestamp_visualizacao})")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Mensagens marcadas como visualizadas!',
                    'timestamp_confirmado': timestamp_visualizacao
                })
                
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Timestamp de visualização inválido'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Timestamp de visualização é obrigatório'
            }, status=400)
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao marcar mensagens como visualizadas: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
def obter_ultima_visualizacao(request, id_chamado):
    """✅ NOVA API: Obter timestamp da última visualização do usuário"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        # ✅ CORREÇÃO: Permitir que COLABORADORES obtenham última visualização
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        # Buscar da sessão o timestamp da última visualização
        timestamp_visualizacao = request.session.get(f'ultima_visualizacao_{id_chamado}')
        
        return JsonResponse({
            'success': True,
            'timestamp_visualizacao': timestamp_visualizacao,
            'timestamp_atual': timezone.now().timestamp()
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao obter última visualização: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

# === NOVAS VIEWS PARA O SISTEMA DE CHAT CORRIGIDO ===

@csrf_exempt
@require_http_methods(["GET", "POST"])  # ✅ CORREÇÃO CRÍTICA: Permitir GET também
@usuario_required
@rate_limit(max_requests=30, window=3600)
def enviar_mensagem_bot_sequencia(request, id_chamado, numero_mensagem):
    """✅ API CORRIGIDA: Enviar mensagem específica da sequência do bot"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO: Permitir que COLABORADORES acessem seus próprios chats
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chat do chamado {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        # Buscar sequência completa
        sequencia = bot_dialogos.get_sequencia_inicial_completa(
            chamado=chamado,
            nome_solicitante=chamado.nome_solicitante,
            departamento=chamado.departamento,
            modalidade_presencial=chamado.modalidade_presencial
        )
        
        # Verificar se o número da mensagem é válido
        if numero_mensagem < 1 or numero_mensagem > len(sequencia):
            return JsonResponse({
                'success': False,
                'message': 'Número de mensagem inválido'
            }, status=400)
        
        # ✅ CORREÇÃO CRÍTICA: Verificar quantas mensagens do bot já existem
        mensagens_existentes = InteracaoChamado.objects.filter(
            chamado=chamado, 
            remetente='bot'
        ).count()
        
        # ✅ CORREÇÃO: Se já temos esta mensagem específica, retornar sucesso mas não criar duplicata
        if mensagens_existentes >= numero_mensagem:
            # Buscar a mensagem existente
            mensagens_bot = InteracaoChamado.objects.filter(
                chamado=chamado, 
                remetente='bot'
            ).order_by('criado_em')
            
            if mensagens_bot.count() >= numero_mensagem:
                mensagem_existente = mensagens_bot[numero_mensagem - 1]
                hora_local = timezone.localtime(mensagem_existente.criado_em)
                
                return JsonResponse({
                    'success': True,
                    'mensagem': mensagem_existente.mensagem,
                    'mensagem_id': str(mensagem_existente.id_interacao),
                    'hora': hora_local.strftime('%H:%M'),
                    'numero_mensagem': numero_mensagem,
                    'total_mensagens': len(sequencia),
                    'ja_existia': True  # ✅ Nova flag para indicar que já existia
                })
        
        # ✅ CORREÇÃO: Se estamos pulando mensagens, criar as anteriores também
        if numero_mensagem > (mensagens_existentes + 1):
            for i in range(mensagens_existentes + 1, numero_mensagem):
                if i <= len(sequencia):
                    mensagem_anterior = sequencia[i - 1]
                    InteracaoChamado.objects.create(
                        chamado=chamado,
                        remetente='bot',
                        mensagem=mensagem_anterior['mensagem'],
                        acao_bot=mensagem_anterior.get('acao_bot', 'mensagem')
                    )
                    logger.info(f"Mensagem {i} do bot criada automaticamente para chamado {chamado.id_legivel}")
        
        # Pegar mensagem específica
        mensagem_data = sequencia[numero_mensagem - 1]
        
        # Criar mensagem no banco
        interacao = InteracaoChamado.objects.create(
            chamado=chamado,
            remetente='bot',
            mensagem=mensagem_data['mensagem'],
            acao_bot=mensagem_data.get('acao_bot', 'mensagem')
        )
        
        hora_local = timezone.localtime(interacao.criado_em)
        
        logger.info(f"Mensagem {numero_mensagem} do bot enviada para chamado {chamado.id_legivel}")
        
        return JsonResponse({
            'success': True,
            'mensagem': mensagem_data['mensagem'],
            'mensagem_id': str(interacao.id_interacao),
            'hora': hora_local.strftime('%H:%M'),
            'numero_mensagem': numero_mensagem,
            'total_mensagens': len(sequencia),
            'ja_existia': False
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em enviar_mensagem_bot_sequencia: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=120, window=3600)
def verificar_status_chamado(request, id_chamado):
    """✅ NOVA API: Verificar status atual do chamado"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        # ✅ CORREÇÃO: Permitir que COLABORADORES verifiquem status dos seus próprios chamados
        if chamado.usuario != request.usuario and request.usuario.tipo_usuario != 'suporte':
            logger.warning(f"Acesso não autorizado ao chamado {id_chamado} por {request.usuario.username}")
            return JsonResponse({
                'success': False,
                'message': 'Acesso não autorizado a este chamado.'
            }, status=403)
        
        return JsonResponse({
            'success': True,
            'chamado_id': str(chamado.id_chamado),
            'chamado_legivel': chamado.id_legivel,
            'status': chamado.status,
            'status_display': chamado.get_status_display(),
            'urgencia': chamado.urgencia,
            'urgencia_display': chamado.get_urgencia_display(),
            'controle_suporte': chamado.controle_chat_suporte,
            'suporte_responsavel': chamado.suporte_responsavel.username if chamado.suporte_responsavel else None,
            'total_mensagens': InteracaoChamado.objects.filter(chamado=chamado).count()
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em verificar_status_chamado: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=50, window=3600)
def reiniciar_sequencia_bot(request, id_chamado):
    """✅ NOVA API: Reiniciar sequência do bot para um chamado"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        if chamado.usuario != request.usuario:
            return JsonResponse({
                'success': False,
                'message': 'Apenas o criador do chamado pode reiniciar a sequência do bot.'
            }, status=403)
        
        # Limpar mensagens existentes do bot (opcional)
        # InteracaoChamado.objects.filter(chamado=chamado, remetente='bot').delete()
        
        # Recriar primeira mensagem
        criar_interacoes_iniciais(chamado, chamado.nome_solicitante, chamado.departamento, chamado.modalidade_presencial)
        
        logger.info(f"Sequência do bot reiniciada para chamado {chamado.id_legivel} por {request.usuario.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Sequência do bot reiniciada com sucesso!'
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao reiniciar sequência do bot: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

# ✅ CORREÇÃO: View para enviar TODA a sequência de uma vez
@csrf_exempt
@require_http_methods(["POST"])
@usuario_required
@rate_limit(max_requests=10, window=3600)
def enviar_sequencia_completa_bot(request, id_chamado):
    """✅ NOVA API: Enviar toda a sequência do bot de uma vez"""
    if not security.validate_uuid(id_chamado):
        return JsonResponse({
            'success': False,
            'message': 'ID de chamado inválido'
        }, status=400)
    
    try:
        chamado = Chamado.objects.get(id_chamado=id_chamado)
        
        if chamado.usuario != request.usuario:
            return JsonResponse({
                'success': False,
                'message': 'Apenas o criador do chamado pode iniciar a sequência do bot.'
            }, status=403)
        
        # Buscar sequência completa
        sequencia = bot_dialogos.get_sequencia_inicial_completa(
            chamado=chamado,
            nome_solicitante=chamado.nome_solicitante,
            departamento=chamado.departamento,
            modalidade_presencial=chamado.modalidade_presencial
        )
        
        # Verificar quantas mensagens já existem
        mensagens_existentes = InteracaoChamado.objects.filter(
            chamado=chamado, 
            remetente='bot'
        ).count()
        
        mensagens_criadas = []
        
        # Criar apenas as mensagens que faltam
        for i in range(mensagens_existentes + 1, len(sequencia) + 1):
            if i <= len(sequencia):
                mensagem_data = sequencia[i - 1]
                interacao = InteracaoChamado.objects.create(
                    chamado=chamado,
                    remetente='bot',
                    mensagem=mensagem_data['mensagem'],
                    acao_bot=mensagem_data.get('acao_bot', 'mensagem')
                )
                
                hora_local = timezone.localtime(interacao.criado_em)
                mensagens_criadas.append({
                    'numero': i,
                    'mensagem': mensagem_data['mensagem'],
                    'mensagem_id': str(interacao.id_interacao),
                    'hora': hora_local.strftime('%H:%M')
                })
                
                logger.info(f"Mensagem {i} do bot criada para chamado {chamado.id_legivel}")
        
        return JsonResponse({
            'success': True,
            'message': f'{len(mensagens_criadas)} mensagens do bot criadas',
            'mensagens_criadas': mensagens_criadas,
            'total_sequencia': len(sequencia),
            'mensagens_ja_existiam': mensagens_existentes
        })
        
    except Chamado.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Chamado não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro em enviar_sequencia_completa_bot: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erro interno do servidor'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@usuario_required
@rate_limit(max_requests=100, window=3600)
def verificar_notificacoes_configuravel(request):
    """✅ NOVA API: Verificar notificações com intervalo configurável (2 minutos)"""
    try:
        # Configuração do intervalo (2 minutos em segundos)
        INTERVALO_VERIFICACAO = 120
        
        # Lógica baseada no tipo de usuário
        if request.usuario.tipo_usuario == 'colaborador':
            notificacoes_nao_lidas = Notificacao.objects.filter(
                chamado__usuario=request.usuario,
                lida=False
            ).order_by('-criado_em')
            
            notificacoes_recentes = Notificacao.objects.filter(
                chamado__usuario=request.usuario
            ).order_by('-criado_em')[:15]  # Mais notificações para colaboradores
            
        else:
            notificacoes_nao_lidas = Notificacao.objects.filter(
                usuario=request.usuario,
                lida=False
            ).order_by('-criado_em')
            
            notificacoes_recentes = Notificacao.objects.filter(
                usuario=request.usuario
            ).order_by('-criado_em')[:20]
        
        notificacoes_data = []
        for notificacao in notificacoes_recentes:
            hora_local = timezone.localtime(notificacao.criado_em)
            notificacoes_data.append({
                'id': str(notificacao.id_notificacao),
                'mensagem': notificacao.mensagem,
                'chamado_id': str(notificacao.chamado.id_chamado) if notificacao.chamado else None,
                'chamado_legivel': notificacao.chamado.id_legivel if notificacao.chamado else 'N/A',
                'hora': hora_local.strftime('%H:%M'),
                'data_completa': hora_local.strftime('%d/%m/%Y %H:%M'),
                'tipo': notificacao.tipo,
                'lida': notificacao.lida,
                'timestamp': notificacao.criado_em.timestamp(),
                'pode_marcar_lida': request.usuario.tipo_usuario == 'suporte'  # ✅ Flag para frontend
            })
        
        return JsonResponse({
            'success': True,
            'notificacoes': notificacoes_data,
            'total_nao_lidas': notificacoes_nao_lidas.count(),
            'ultima_verificacao': timezone.now().timestamp(),
            'tipo_usuario': request.usuario.tipo_usuario,
            'intervalo_verificacao': INTERVALO_VERIFICACAO,
            'permite_gerenciar_notificacoes': request.usuario.tipo_usuario == 'suporte'
        })
        
    except Exception as e:
        logger.error(f"Erro em verificar_notificacoes_configuravel: {str(e)}")
        return JsonResponse({
            'success': False,
            'notificacoes': [],
            'total_nao_lidas': 0,
            'message': 'Erro ao carregar notificações'
        })