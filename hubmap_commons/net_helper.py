from datetime import datetime
import requests

#check a hubmap service
#if it returns a 200 from the standard /status call
#within 2 seconds return the number of milliseconds it took
#to return
#
#   input- service_url: the url of the service (e.g. https://uuid.api.hubmapconsortium.org)
# outputs- on success: an integer representing the number of milliseconds the status call took
#          on failure: the boolean False
def check_hm_ws(service_url):
    start_time = datetime.now()
    try:
        failed = False
        url = service_url.strip()
        if url.endswith('/'): url = url[:len(url) - 1]
        if not url.endswith('/status'):
            url = url + "/status"
        resp = requests.get(url, timeout=2)
        if resp.ok == False: failed = True
    except Exception:
        failed = True
    finally:
        end_time = datetime.now()
        time_diff = end_time - start_time
        elapsed_time_millis = int((time_diff.seconds * 1000) + (time_diff.microseconds / 1000))
        if failed:
            return False
        else:
            return elapsed_time_millis

#print(str(check_hm_ws('https://uuid-api.refactor.hubmapconsortium.org/status/')))
