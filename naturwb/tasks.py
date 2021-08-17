# the sheduled tasks to perform
from .models import SavedResults
import datetime

def delete_saved_results(hours=2):
    """
    Deletes all Discounts that are more than 2 hours old
    """
    twohours_ago = datetime.datetime.now() - datetime.timedelta(hours=hours)
    expired_results = SavedResults.objects.filter(
        timestamp__lte=twohours_ago
    )
    expired_results.delete()