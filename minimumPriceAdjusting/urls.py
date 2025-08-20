
from django.contrib import admin
from django.urls import include, path
from example_app.views import hello_rest_api, upload_excel, process_excel_and_download, process_excel_with_preview
from rest_framework import routers
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


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/', include('rest_framework.urls')),
    path('api/hello/', hello_rest_api, name='hello_rest_api'),
    path('api/upload-excel/', upload_excel, name='upload_excel'),
    path('api/process-excel-download/', process_excel_and_download, name='process_excel_download'),
    path('api/process-excel-preview/', process_excel_with_preview, name='process_excel_preview'),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
