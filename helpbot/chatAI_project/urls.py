from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from app_project.api import viewsets as app_project_viewsets
from app_project import views

# Configuração das rotas API
route = routers.DefaultRouter()
route.register(r'usuarios', app_project_viewsets.UsuarioViewSet)

urlpatterns = [
    # ✅ CORREÇÃO: Página inicial correta
    path('', views.home, name='home'),  
    
    # ✅ CORREÇÃO: Dashboard principal
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Logout
    path('logout/', views.logout_usuario, name='logout_usuario'),
    
    # API REST
    path('api/', include(route.urls)),
    path('api/info/', views.api_info, name='api_info'),  
    
    # ✅ CORREÇÃO: Todos chamados (apenas para suporte)
    path('todos-chamados/', views.todos_chamados, name='todos_chamados'),
    
    # URLs PARA LISTAGEM DE CHAMADOS
    path('meus-chamados/', views.meus_chamados, name='meus_chamados'),
    
    # Sistema de Chamados (Página de NOVO chamado)
    path('chamados/', views.sistema_chamados, name='sistema_chamados'),
    
    # URLs DO CHAMADO INDIVIDUAL 
    path('chamado/<uuid:id_chamado>/', views.detalhes_chamado, name='detalhes_chamado'),
    path('chamado/<uuid:id_chamado>/carregar-mensagens/', views.carregar_mensagens_chat, name='carregar_mensagens_chat'),
    path('chamado/<uuid:id_chamado>/proxima-mensagem/', views.proxima_mensagem_bot, name='proxima_mensagem_bot'),
    
    # ✅ URL PARA ENVIAR MENSAGEM
    path('chamado/<uuid:id_chamado>/enviar-mensagem/', views.enviar_mensagem, name='enviar_mensagem'),
    
    # ✅ URLs PARA O SISTEMA DE CHAT CORRIGIDO
    path('chamado/<uuid:id_chamado>/enviar-mensagem-bot/<int:numero_mensagem>/', views.enviar_mensagem_bot_sequencia, name='enviar_mensagem_bot_sequencia'),
    path('chamado/<uuid:id_chamado>/verificar-status/', views.verificar_status_chamado, name='verificar_status_chamado'),
    path('chamado/<uuid:id_chamado>/reiniciar-sequencia/', views.reiniciar_sequencia_bot, name='reiniciar_sequencia_bot'),
    
    # ✅ URL PARA SEQUÊNCIA COMPLETA
    path('chamado/<uuid:id_chamado>/enviar-sequencia-completa/', views.enviar_sequencia_completa_bot, name='enviar_sequencia_completa_bot'),
    
    # URLs PARA CONFIRMAÇÕES (CHAMADO INDIVIDUAL) 
    path('chamado/<uuid:id_chamado>/confirmar-atendimento/', views.confirmar_atendimento, name='confirmar_atendimento'),
    path('chamado/<uuid:id_chamado>/usuario-confirmar-resolucao/', views.usuario_confirmar_resolucao, name='usuario_confirmar_resolucao'),
    
    # URLs PARA ATUALIZAÇÃO DE STATUS
    path('chamado/<uuid:id_chamado>/atualizar-status/', views.atualizar_status_chamado, name='atualizar_status_chamado'),
    path('chamado/<uuid:id_chamado>/verificar-novas-mensagens/', views.verificar_novas_mensagens, name='verificar_novas_mensagens'),
    path('chamado/<uuid:id_chamado>/verificar-mensagens-inteligente/', views.verificar_novas_mensagens_inteligente, name='verificar_mensagens_inteligente'),
    
    # ✅ APIs de suporte
    path('api/chamados/recentes/', views.api_chamados_recentes, name='api_chamados_recentes'),
    path('api/intermediar-chat/<uuid:id_chamado>/', views.intermediar_chat_bot, name='intermediar_chat'),
    path('api/trocar-status/<uuid:id_chamado>/', views.trocar_status_chamado, name='trocar_status'),
    path('api/dados-grafico/', views.api_dados_grafico, name='api_dados_grafico'),
    
    # URLs PARA NOTIFICAÇÕES
    path('notificacoes/', views.carregar_notificacoes, name='carregar_notificacoes'),
    path('notificacoes/<uuid:id_notificacao>/marcar-lida/', views.marcar_notificacao_lida, name='marcar_notificacao_lida'),
    
    
    # ✅ URLs PARA SISTEMA DE NOTIFICAÇÕES CORRIGIDO
    path('api/verificar-notificacoes/', views.verificar_notificacoes, name='verificar_notificacoes'),
    path('api/marcar-todas-notificacoes-lidas/', views.marcar_todas_notificacoes_lidas, name='marcar_todas_notificacoes_lidas'),
    path('api/limpar-notificacoes/', views.limpar_notificacoes, name='limpar_notificacoes'),
    path('api/notificacoes/pendentes/', views.verificar_notificacoes_pendentes_suporte, name='verificar_notificacoes_pendentes'),
    path('api/chamados/pendentes/', views.verificar_chamados_pendentes_globais, name='verificar_chamados_pendentes'),
    path('api/notificacoes/limpar-resolvidos/', views.limpar_notificacoes_chamados_resolvidos, name='limpar_notificacoes_resolvidos'),
    path('api/chamados/abertos-para-suporte/', views.verificar_chamados_abertos_para_suporte, name='verificar_chamados_abertos_suporte'),

    # URLs PARA SUPORTE
    path('chamado/<uuid:id_chamado>/marcar-visualizado/', views.marcar_chamado_visualizado, name='marcar_chamado_visualizado'),
    path('chamado/<uuid:id_chamado>/assumir-controle/', views.assumir_controle_chat, name='assumir_controle_chat'),
    path('chamado/<uuid:id_chamado>/enviar-mensagem-suporte/', views.enviar_mensagem_suporte, name='enviar_mensagem_suporte'),
    
    # ✅ URLs PARA CONTROLE DE VISUALIZAÇÃO
    path('chamado/<uuid:id_chamado>/marcar-mensagens-visualizadas/',  views.marcar_mensagens_visualizadas,  name='marcar_mensagens_visualizadas'),
    path('chamado/<uuid:id_chamado>/obter-ultima-visualizacao/',  views.obter_ultima_visualizacao,  name='obter_ultima_visualizacao'),

    # ✅ NOVAS URLs CRÍTICAS PARA NOTIFICAÇÕES
    path('api/notificacoes/<uuid:id_notificacao>/marcar-como-lida/', views.marcar_notificacao_como_lida, name='marcar_notificacao_como_lida'),
    path('api/notificacoes/obter/', views.obter_notificacoes_usuario, name='obter_notificacoes_usuario'),
    path('api/notificacoes/verificar/', views.verificar_notificacoes, name='verificar_notificacoes'),
    path('api/notificacoes/marcar-todas-lidas/', views.marcar_todas_notificacoes_lidas, name='marcar_todas_notificacoes_lidas'),
    path('api/notificacoes/limpar/', views.limpar_notificacoes, name='limpar_notificacoes'),

    # Admin
    path('admin/', admin.site.urls),
]