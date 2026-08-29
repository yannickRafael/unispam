import re
import requests

BASE_URL = "https://campus.isutc.ac.mz"
AJAX_URL = f"{BASE_URL}/lib/ajax/service.php"

# Accept text/html for page loads, json for AJAX — session handles both
_HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0",
}
_HEADERS_AJAX = {
    **_HEADERS_BASE,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


class MoodleClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(_HEADERS_BASE)
        self.sesskey = None
        self.userid = None

    def _parse_cfg(self, html: str) -> None:
        m = re.search(r'"sesskey"\s*:\s*"([^"]+)"', html)
        if m:
            self.sesskey = m.group(1)
        m = re.search(r'"[Uu]ser[Ii]d"\s*:\s*(\d+)', html)
        if m:
            self.userid = int(m.group(1))

    def login(self, username: str, password: str) -> None:
        r = self.session.get(f"{BASE_URL}/login/index.php")
        r.raise_for_status()
        m = re.search(r'name="logintoken"\s+value="([^"]+)"', r.text)
        if not m:
            raise RuntimeError("logintoken not found")
        logintoken = m.group(1)

        r = self.session.post(
            f"{BASE_URL}/login/index.php",
            data={"logintoken": logintoken, "username": username, "password": password},
            allow_redirects=True,
        )
        r.raise_for_status()
        self._parse_cfg(r.text)

        # Redirect chain may not land on /my/ — fetch it explicitly to get M.cfg
        if not self.sesskey or not self.userid:
            r = self.session.get(f"{BASE_URL}/my/")
            r.raise_for_status()
            self._parse_cfg(r.text)

        if not self.sesskey:
            raise RuntimeError("Login failed — sesskey not found (bad credentials?)")
        if not self.userid:
            raise RuntimeError("Login succeeded but userid not found in page")

    def _call(self, methodname: str, args: dict) -> object:
        payload = [{"index": 0, "methodname": methodname, "args": args}]
        r = self.session.post(
            AJAX_URL,
            params={"sesskey": self.sesskey, "info": methodname},
            json=payload,
            headers=_HEADERS_AJAX,
        )
        r.raise_for_status()
        result = r.json()
        if result[0].get("error"):
            raise RuntimeError(f"API error [{methodname}]: {result[0].get('exception', result[0])}")
        return result[0]["data"]

    def send_message(self, touserid: int, text: str) -> dict:
        data = self._call(
            "core_message_send_instant_messages",
            {"messages": [{"touserid": touserid, "text": text, "textformat": 0}]},
        )
        return data[0] if data else {}

    def search_users(self, query: str, limitnum: int = 51, limitfrom: int = 0) -> list[dict]:
        data = self._call(
            "core_message_message_search_users",
            {
                "userid": str(self.userid),
                "search": query,
                "limitnum": limitnum,
                "limitfrom": limitfrom,
            },
        )
        return data.get("contacts", []) + data.get("noncontacts", [])
