# urls.py - CORRIGIDO E LIMPO
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from app_project.api import viewsets as app_project_viewsets
from app_project import views

# Configuração das rotas API
route = routers.DefaultRouter()
route.register(r'usuarios', app_project_viewsets.UsuarioViewSet)

urlpatterns = [
    # Página inicial
    path('', views.home, name='home'),  
    
    # Logout
    path('logout/', views.logout_usuario, name='logout_usuario'),
    
    # API REST
    path('api/', include(route.urls)),
    path('api/info/', views.api_info, name='api_info'),  
    
    # Dashboard (Página principal após login para TODOS os usuários)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # URLs PARA LISTAGEM DE CHAMADOS
    path('meus-chamados/', views.meus_chamados, name='meus_chamados'),     # 'meus_chamados' agora é efetivamente o dashboard do colaborador
    path('todos-chamados/', views.todos_chamados, name='todos_chamados'),   # 'todos_chamados' é o dashboard do admin (acessível também por /dashboard/)
    
    # Sistema de Chamados (Página de NOVO chamado)
    path('chamados/', views.sistema_chamados, name='sistema_chamados'),
    
    # URLs DO CHAMADO INDIVIDUAL 
    path('chamado/<uuid:id_chamado>/', views.detalhes_chamado, name='detalhes_chamado'),
    path('chamado/<uuid:id_chamado>/carregar-mensagens/', views.carregar_mensagens_chat, name='carregar_mensagens_chat'),
    path('chamado/<uuid:id_chamado>/proxima-mensagem/', views.proxima_mensagem_bot, name='proxima_mensagem_bot'),
    path('chamado/<uuid:id_chamado>/enviar-mensagem/', views.enviar_mensagem, name='enviar_mensagem'),
    
    # URLs PARA CONFIRMAÇÕES (CHAMADO INDIVIDUAL) 
    path('chamado/<uuid:id_chamado>/confirmar-atendimento/', views.confirmar_atendimento, name='confirmar_atendimento'),
    path('chamado/<uuid:id_chamado>/usuario-confirmar-resolucao/', views.usuario_confirmar_resolucao, name='usuario_confirmar_resolucao'),
    
    # URLs PARA ATUALIZAÇÃO DE STATUS
    path('chamado/<uuid:id_chamado>/atualizar-status/', views.atualizar_status_chamado, name='atualizar_status_chamado'),
    path('chamado/<uuid:id_chamado>/verificar-novas-mensagens/', views.verificar_novas_mensagens, name='verificar_novas_mensagens'),
    path('chamado/<uuid:id_chamado>/verificar-mensagens-inteligente/', views.verificar_novas_mensagens_inteligente, name='verificar_mensagens_inteligente'),
    path('api/chamados/recentes/', views.api_chamados_recentes, name='api_chamados_recentes'),
    
    # URLs PARA NOTIFICAÇÕES
    path('notificacoes/', views.carregar_notificacoes, name='carregar_notificacoes'),
    path('notificacoes/<uuid:id_notificacao>/marcar-lida/', views.marcar_notificacao_lida, name='marcar_notificacao_lida'),
    
    # Admin
    path('admin/', admin.site.urls),
]