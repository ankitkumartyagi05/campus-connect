from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_session
from app.application.auth_service import AuthService
from fastapi.responses import RedirectResponse, HTMLResponse
from app.core.security import create_access_token
from app.core.config import settings
from app.domain.models import User, UserProfile, OAuthIdentity
from sqlalchemy import select
import uuid
from app.core.security import get_password_hash
import httpx
import urllib.parse

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register")
@router.post("/register/")
async def register(request: Request, session: AsyncSession = Depends(get_session)):
    # accept JSON or form data
    if request.headers.get('content-type', '').startswith('application/json'):
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        role = data.get('role', 'STUDENT')
    else:
        form = await request.form()
        email = form.get('email')
        password = form.get('password')
        full_name = form.get('full_name')
        role = form.get('role', 'STUDENT')

    if not email or not password or not full_name:
        raise HTTPException(status_code=400, detail='email, password and full_name are required')

    service = AuthService(session)
    try:
        return await service.register(email, password, full_name, role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/register')
async def register_get():
    return HTMLResponse('<html><body><p>Use POST /api/v1/auth/register with form-encoded fields: email, password, full_name</p></body></html>')


@router.options('/register')
@router.options('/register/')
async def register_options():
    return HTMLResponse('', status_code=200)

@router.post("/login")
@router.post("/login/")
async def login(request: Request, session: AsyncSession = Depends(get_session)):
    # accept JSON or form data
    if request.headers.get('content-type', '').startswith('application/json'):
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
    else:
        form = await request.form()
        email = form.get('email')
        password = form.get('password')

    if not email or not password:
        raise HTTPException(status_code=400, detail='email and password are required')

    service = AuthService(session)
    try:
        return await service.login(email, password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get('/login')
async def login_get():
    return HTMLResponse('<html><body><p>Use POST /api/v1/auth/login with form-encoded fields: email, password</p></body></html>')


@router.options('/login')
@router.options('/login/')
async def login_options():
    return HTMLResponse('', status_code=200)


@router.get("/oauth/{provider}")
async def oauth_start(provider: str, request: Request):
    provider = provider.lower()
    # If provider credentials are not configured, fall back to demo simulate
    client_id = getattr(settings, f"{provider.upper()}_CLIENT_ID", None)
    client_secret = getattr(settings, f"{provider.upper()}_CLIENT_SECRET", None)
    if not client_id or not client_secret:
        return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))

    # Build a redirect_uri that matches provider app settings
    if settings.OAUTH_CALLBACK_BASE:
        callback_base = settings.OAUTH_CALLBACK_BASE.rstrip('/')
        redirect_uri = f"{callback_base}/api/v1/auth/oauth/{provider}/callback"
    else:
        scheme = request.url.scheme
        host = request.headers.get('host')
        redirect_uri = f"{scheme}://{host}/api/v1/auth/oauth/{provider}/callback"

    if provider == 'google':
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    elif provider == 'github':
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'read:user user:email'
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    elif provider == 'linkedin':
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'r_liteprofile r_emailaddress'
        }
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"
    else:
        return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))

    return RedirectResponse(url=auth_url)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, session: AsyncSession = Depends(get_session)):
    provider = provider.lower()
    code = request.query_params.get('code')
    if not code:
        return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))

    client_id = getattr(settings, f"{provider.upper()}_CLIENT_ID", None)
    client_secret = getattr(settings, f"{provider.upper()}_CLIENT_SECRET", None)
    if not client_id or not client_secret:
        return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))

    if settings.OAUTH_CALLBACK_BASE:
        callback_base = settings.OAUTH_CALLBACK_BASE.rstrip('/')
        redirect_uri = f"{callback_base}/api/v1/auth/oauth/{provider}/callback"
    else:
        scheme = request.url.scheme
        host = request.headers.get('host')
        redirect_uri = f"{scheme}://{host}/api/v1/auth/oauth/{provider}/callback"

    async with httpx.AsyncClient() as client:
        try:
            provider_user_id = None
            if provider == 'google':
                token_resp = await client.post('https://oauth2.googleapis.com/token', data={
                    'code': code,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }, headers={'Accept': 'application/json'})
                token_json = token_resp.json()
                access_token = token_json.get('access_token')
                id_token = token_json.get('id_token')
                # Prefer verified id_token info when available
                if id_token:
                    info_resp = await client.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': id_token})
                    if info_resp.is_success:
                        info = info_resp.json()
                        provider_user_id = info.get('sub')
                        email = info.get('email')
                        full_name = info.get('name') or info.get('email').split('@')[0] if info.get('email') else 'User'
                    else:
                        userinfo = await client.get('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': f'Bearer {access_token}'})
                        profile = userinfo.json()
                        provider_user_id = profile.get('sub')
                        email = profile.get('email')
                        full_name = profile.get('name') or profile.get('given_name') or (email.split('@')[0] if email else 'User')
                else:
                    userinfo = await client.get('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': f'Bearer {access_token}'})
                    profile = userinfo.json()
                    provider_user_id = profile.get('sub')
                    email = profile.get('email')
                    full_name = profile.get('name') or profile.get('given_name') or (email.split('@')[0] if email else 'User')
            elif provider == 'github':
                token_resp = await client.post('https://github.com/login/oauth/access_token', data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri
                }, headers={'Accept': 'application/json'})
                token_json = token_resp.json()
                access_token = token_json.get('access_token')
                user_resp = await client.get('https://api.github.com/user', headers={'Authorization': f'token {access_token}', 'Accept': 'application/json'})
                user_json = user_resp.json()
                provider_user_id = str(user_json.get('id')) if user_json.get('id') else None
                email = user_json.get('email')
                if not email:
                    emails_resp = await client.get('https://api.github.com/user/emails', headers={'Authorization': f'token {access_token}', 'Accept': 'application/json'})
                    emails = emails_resp.json() or []
                    primary = next((e['email'] for e in emails if e.get('primary') and e.get('verified')), None)
                    email = primary or (emails[0]['email'] if emails else None)
                full_name = user_json.get('name') or user_json.get('login') or (email.split('@')[0] if email else 'User')
            elif provider == 'linkedin':
                token_resp = await client.post('https://www.linkedin.com/oauth/v2/accessToken', data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'client_id': client_id,
                    'client_secret': client_secret
                }, headers={'Accept': 'application/json'})
                token_json = token_resp.json()
                access_token = token_json.get('access_token')
                headers = {'Authorization': f'Bearer {access_token}', 'X-Restli-Protocol-Version': '2.0.0'}
                me = await client.get('https://api.linkedin.com/v2/me', headers=headers)
                me_json = me.json()
                provider_user_id = me_json.get('id') if me_json.get('id') else None
                email_resp = await client.get('https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))', headers=headers)
                email_json = email_resp.json()
                try:
                    email = email_json['elements'][0]['handle~']['emailAddress']
                except Exception:
                    email = None
                full_name = ((me_json.get('localizedFirstName') or '') + ' ' + (me_json.get('localizedLastName') or '')).strip() or (email.split('@')[0] if email else 'User')
            else:
                return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))
        except Exception:
            return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))

    if not email:
        return RedirectResponse(url=request.url_for("oauth_simulate", provider=provider))

    # find by oauth identity first
    if provider_user_id:
        q = await session.execute(select(OAuthIdentity).where(OAuthIdentity.provider == provider, OAuthIdentity.provider_user_id == str(provider_user_id)))
        oauth = q.scalars().first()
    else:
        oauth = None

    user = None
    if oauth:
        q = await session.execute(select(User).where(User.id == oauth.user_id))
        user = q.scalars().first()

    # If no user via identity, try by email and link account
    if not user and email:
        q = await session.execute(select(User).where(User.email == email))
        user = q.scalars().first()
        if user and provider_user_id:
            # link identity
            oi = OAuthIdentity(provider=provider, provider_user_id=str(provider_user_id), user_id=user.id)
            session.add(oi)
            await session.commit()

    # If still no user, create account and link
    if not user:
        user_id = str(uuid.uuid4())
        pw = get_password_hash(uuid.uuid4().hex)
        user = User(id=user_id, email=email or f"{provider}_user_{user_id}@noemail.local", password_hash=pw, role="STUDENT", is_verified=True)
        profile = UserProfile(user_id=user_id, full_name=full_name, skills=[], goals=[])
        session.add(user)
        session.add(profile)
        await session.commit()
        if provider_user_id:
            oi = OAuthIdentity(provider=provider, provider_user_id=str(provider_user_id), user_id=user.id)
            session.add(oi)
            await session.commit()

    token = create_access_token({"sub": user.id})
    html = f"""
    <html><body>
    <script>
        try {{
            const token = "{token}";
            const provider = "{provider}";
            if(window.opener){{
                window.opener.postMessage({{type:'oauth', provider: provider, token: token}}, window.location.origin);
                window.close();
            }} else {{
                document.write('Token: ' + token);
            }}
        }} catch(e){{ document.write('OAuth complete. Close this window.'); }}
    </script>
    </body></html>
    """
    return HTMLResponse(content=html)


@router.get('/ping')
async def ping():
    return {"ok": True}


@router.get("/oauth/{provider}/simulate")
async def oauth_simulate(provider: str, session: AsyncSession = Depends(get_session)):
        # create or find a demo user for this provider
        email = f"{provider}_demo@campus.local"
        q = await session.execute(select(User).where(User.email == email))
        user = q.scalars().first()
        if not user:
                user_id = str(uuid.uuid4())
                pw = get_password_hash(uuid.uuid4().hex)
                user = User(id=user_id, email=email, password_hash=pw, role="STUDENT", is_verified=True)
                profile = UserProfile(user_id=user_id, full_name=f"{provider.title()} Demo", skills=[], goals=[])
                session.add(user)
                session.add(profile)
                await session.commit()
        token = create_access_token({"sub": user.id})
        html = f"""
        <html><body>
        <script>
            try {{
                const token = "{token}";
                const provider = "{provider}";
                if(window.opener){{
                    window.opener.postMessage({{type:'oauth', provider: provider, token: token}}, window.location.origin);
                    window.close();
                }} else {{
                    document.write('Token: ' + token);
                }}
            }} catch(e){{ document.write('OAuth simulation complete. Close this window.'); }}
        </script>
        </body></html>
        """
        return HTMLResponse(content=html)