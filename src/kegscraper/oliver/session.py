import pprint
import httpx
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

from .utils import api_fetch
from kegscraper.util.commons import eval_inputs, consume_json

def login(username: str, password: str):
    client = httpx.Client()
    client.headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    }

    resp = client.get("https://kegs.oliverasp.co.uk/library/home/news")
    soup = BeautifulSoup(resp.text, "html.parser")
    inputs = eval_inputs(soup)
    pprint.pp(inputs) 
    resp = client.get("https://kegs.oliverasp.co.uk/library/home/news",
                      params=inputs)
    soup = BeautifulSoup(resp.text, "html.parser")
    print(soup.prettify())

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
    assert isinstance(data, dict)

    corporation = inputs["corporationAlias"]
    login_dialog = data["loginDialog"]
    pkm: str = login_dialog["publicKeyModulus"]
    pke: str = login_dialog["publicKeyExponent"]
    sid: str = login_dialog["sessionId"]
    # sid = client.cookies.get("JSESSIONID")
    
    jpass = oliver_rsa(pkm, pke, sid, password).hex()
    print(inputs)

    resp = client.post("https://kegs.oliverasp.co.uk/library/ClientLookup", data={
        "corporation": corporation,
        "afterLoginUuid": "",
        "afterLoginAction": "",
        "url": "",
        "j_password": jpass,
        "j_username": username
    })
    print(resp)

    resp = client.get("https://kegs.oliverasp.co.uk/library/home/api/borrower/details")
    print(resp.content)
    print(client.cookies)


def oliver_rsa(pkm: str, pke: str, sid: str, password: str) -> bytes:
    n = int(pkm, 16)
    e = int(pke, 16)
    pn = rsa.RSAPublicNumbers(
        e, n
    )
    pubkey = pn.public_key()
    return pubkey.encrypt((sid + password).encode("utf-8"),
                          padding.PKCS1v15()
                          )
