# This script is to help identify the O/S location of a Data Product so that it can be found & displayed under Django.
#  To specify the Data Product to display, first find it in the database and get the id of it.
#  Put that id into the DataProduct .get command, as in dp = DataProduct.objects.select_related('fileFormat').get(id=1)
python manage.py shell -c "
from apps.observations.models import DataProduct
from django.conf import settings
from pathlib import Path

dp = DataProduct.objects.select_related('fileFormat').get(id=1)

media_root = Path(settings.MEDIA_ROOT).resolve()
dp_path = str(dp.path or '').strip('/')
file_name = str(dp.fileName or '').lstrip('/')

computed_path = media_root / dp_path / file_name
computed_url = settings.MEDIA_URL.rstrip('/') + '/' + dp_path + '/' + file_name

print('DataProduct id:', dp.id)
print('MEDIA_ROOT from Django:', settings.MEDIA_ROOT)
print('MEDIA_ROOT absolute:', media_root)
print('DataProduct.path:', repr(dp.path))
print('DataProduct.fileName:', repr(dp.fileName))
print('DataProduct fileFormat:', getattr(dp.fileFormat, 'fileFormat', None))
print('Computed filesystem path:', computed_path)
print('Computed public URL:', computed_url)
print('Exists:', computed_path.exists())
print('Is file:', computed_path.is_file())
"
