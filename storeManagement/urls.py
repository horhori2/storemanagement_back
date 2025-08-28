
from django.contrib import admin
from django.urls import include, path
from minimumPriceApp.views import upload_excel, process_excel_and_download, process_excel_with_preview, update_excel_file
from cardStockManageApp.views import TCGGameViewSet, CardSetViewSet, CardViewSet, CardVersionViewSet, InventoryViewSet, SaleViewSet
from rest_framework import routers
from rest_framework.routers import DefaultRouter
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="Book API",
        default_version='v1',
        description='API for managing books',
        terms_of_service="hhtps://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
)

router = DefaultRouter()
router.register(r'games', TCGGameViewSet)
router.register(r'sets', CardSetViewSet)
router.register(r'cards', CardViewSet)
router.register(r'card-versions', CardVersionViewSet)
router.register(r'inventory', InventoryViewSet)
router.register(r'sales', SaleViewSet, basename='sale')


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # path('api/', include('rest_framework.urls')),
    path('api/', include(router.urls)),
    path('api/upload-excel/', upload_excel, name='upload_excel'),
    path('api/process-excel-download/', process_excel_and_download, name='process_excel_download'),
    path('api/process-excel-preview/', process_excel_with_preview, name='process_excel_preview'),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/excel/update/', update_excel_file, name='update_excel'),
]


