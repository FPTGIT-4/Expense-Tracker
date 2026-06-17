from django.urls import path
from .views import MainIOView, ExportView, ImportView, DownloadSampleTemplateView, DownloadImportLogView

app_name = 'data_io'

urlpatterns = [
    path('', MainIOView.as_view(), name='main'),
    path('export/', ExportView.as_view(), name='export'),
    path('import/', ImportView.as_view(), name='import'),
    path('import/log/', DownloadImportLogView.as_view(), name='import_log'),
    path('sample-template/', DownloadSampleTemplateView.as_view(), name='sample_template'),
]
