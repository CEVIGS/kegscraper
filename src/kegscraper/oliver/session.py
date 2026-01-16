import httpx

from bs4 import BeautifulSoup
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import rsa, padding

from kegscraper.util.commons import eval_inputs, consume_json

@dataclass
class Session:
    rq: httpx.Client
    username: str
       

def login(username: str, password: str):
    client = httpx.Client(
        headers={}  # add user agent here if you want
    )

    resp = client.get("https://kegs.oliverasp.co.uk/library/home/news")
    soup = BeautifulSoup(resp.text, "html.parser")
    inputs = eval_inputs(soup)

    resp = client.get("https://kegs.oliverasp.co.uk/library/home/news",
                      params=inputs)
    soup = BeautifulSoup(resp.text, "html.parser")
    search_str = "LOGIN_DATA = {"
    data = None
    for script in soup.find_all("script", {"type": "text/javascript"}):
        text = script.text
        if search_str in text:
            data = consume_json(
                text, text.find(search_str) + len("LOGIN_DATA = ")
            )
            break

    assert data is not None, "Could not find login data"
    assert isinstance(data, dict), f"Unknown data: {data}"

    corporation: str = inputs["corporationAlias"]
    login_dialog: dict[str, str] = data["loginDialog"]
    pkm: str = login_dialog["publicKeyModulus"]
    pke: str = login_dialog["publicKeyExponent"]
    sid: str = login_dialog["sessionId"]
    
    jpass = oliver_rsa(pkm, pke, sid, password).hex()
    resp = client.post("https://kegs.oliverasp.co.uk/library/ClientLookup", data={
        "corporation": corporation,
        "afterLoginUuid": "",
        "afterLoginAction": "",
        "url": "",
        "j_password": jpass,
        "j_username": username
    })
    
    return Session(
        rq=client,
        username=username
    )


def oliver_rsa(pkm: str, pke: str, sid: str, password: str) -> bytes:
    n = int(pkm, 16)
    e = int(pke, 16)
    pn = rsa.RSAPublicNumbers(e, n)
    pubkey = pn.public_key()
    return pubkey.encrypt((sid + password).encode("utf-8"),
                          padding.PKCS1v15()
                          )
