import os
from django.conf import settings

def get_plot_path(filename):
    """Generates a clean path for plot files, ensuring no redundant directory nesting."""
    base_dir = getattr(settings, 'MEDIA_ROOT', 'media')
    # Ensure we are targeting the 'plots' subdirectory directly under MEDIA_ROOT
    return os.path.join(base_dir, 'plots', os.path.basename(filename))
