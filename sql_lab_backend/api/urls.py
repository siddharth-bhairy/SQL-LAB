from django.urls import path
from .views import validate_sql,get_sql_hint,get_schema_summary

urlpatterns = [
    path('validate/', validate_sql, name='validate_sql'),
    path('hint/', get_sql_hint, name='get_sql_hint'),
    path('summary/', get_schema_summary, name='get_schema_summary'),
]