# urls.py (앱 레벨)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router 설정
router = DefaultRouter()
router.register(r'games', views.TCGGameViewSet, basename='tcggame')
router.register(r'sets', views.CardSetViewSet, basename='cardset')
router.register(r'cards', views.CardViewSet, basename='card')
router.register(r'card-versions', views.CardVersionViewSet, basename='cardversion')
router.register(r'inventory', views.InventoryViewSet, basename='inventory')
router.register(r'sales', views.SaleViewSet, basename='sale')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # 추가 커스텀 엔드포인트들
    path('api/games/<slug:slug>/sets/', views.GameSetsView.as_view(), name='game-sets'),
    path('api/sets/<str:set_code>/cards/', views.SetCardsView.as_view(), name='set-cards'),
]

# 프로젝트 레벨 urls.py에도 추가
# from django.urls import path, include
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('your_app_name.urls')),  # 앱 이름으로 변경
# ]