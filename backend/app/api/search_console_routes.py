"""
Google Search Console API Routes - OAuth2 e busca de dados.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import os
import json

from app.db.session import SessionLocal
from app.models.models import Project
from app.core.encryption import encrypt_token


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/api/search-console", tags=["search-console"])

# Configuração OAuth2
def get_client_config():
    """Retorna configuração do cliente OAuth2."""
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": [
                "http://localhost:8000/api/search-console/callback",
                "http://129.148.63.199/api/search-console/callback"  # Produção
            ],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']


@router.get("/connect")
def connect_search_console(
    project_id: str = Query(..., description="ID do projeto"),
    db: Session = Depends(get_db)
):
    """
    Inicia fluxo OAuth2 para conectar Google Search Console.
    
    Retorna URL de autorização para o usuário.
    """
    try:
        from google_auth_oauthlib.flow import Flow
        
        # Verificar se projeto existe
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Verificar se credenciais estão configuradas
        client_config = get_client_config()
        if not client_config["web"]["client_id"]:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
            )
        
        # Criar flow OAuth2
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=client_config["web"]["redirect_uris"][0]
        )
        
        # Gerar URL de autorização
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=project_id,  # Passar project_id no state
            prompt='consent'  # Forçar consent para obter refresh token
        )
        
        return {
            "authorization_url": authorization_url,
            "project_id": project_id,
            "status": "pending_authorization"
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth libraries not installed. Run: pip install google-auth-oauthlib"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating OAuth: {str(e)}")


@router.get("/callback")
def oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db)
):
    """
    Callback OAuth2 - recebe código de autorização e salva credenciais.
    """
    try:
        from google_auth_oauthlib.flow import Flow
        
        project_id = state
        
        # Buscar projeto
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Criar flow OAuth2
        client_config = get_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=client_config["web"]["redirect_uris"][0]
        )
        
        # Trocar código por token
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Serializar credenciais
        credentials_json = json.dumps({
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        })
        
        # Criptografar e salvar
        encrypted_token = encrypt_token(credentials_json)
        project.search_console_token = encrypted_token
        project.search_console_connected_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "connected",
            "project_id": project_id,
            "connected_at": project.search_console_connected_at.isoformat(),
            "message": "Google Search Console connected successfully!"
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth libraries not installed"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error in OAuth callback: {str(e)}")


@router.post("/disconnect")
def disconnect_search_console(
    project_id: str = Query(..., description="ID do projeto"),
    db: Session = Depends(get_db)
):
    """
    Desconecta Google Search Console do projeto.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.search_console_token = None
    project.search_console_connected_at = None
    project.search_console_site_url = None
    
    db.commit()
    
    return {
        "status": "disconnected",
        "project_id": project_id
    }


@router.get("/status")
def get_connection_status(
    project_id: str = Query(..., description="ID do projeto"),
    db: Session = Depends(get_db)
):
    """
    Verifica status da conexão com Search Console.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    is_connected = bool(project.search_console_token)
    
    return {
        "project_id": project_id,
        "is_connected": is_connected,
        "connected_at": project.search_console_connected_at.isoformat() if project.search_console_connected_at else None,
        "site_url": project.search_console_site_url
    }


@router.post("/set-site-url")
def set_site_url(
    project_id: str = Query(..., description="ID do projeto"),
    site_url: str = Query(..., description="URL do site (ex: https://exemplo.com)"),
    db: Session = Depends(get_db)
):
    """
    Define a URL do site no Search Console para este projeto.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.search_console_token:
        raise HTTPException(
            status_code=400,
            detail="Search Console not connected. Connect first."
        )
    
    # Validar formato da URL
    if not site_url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=400,
            detail="Site URL must start with http:// or https://"
        )
    
    project.search_console_site_url = site_url
    db.commit()
    
    return {
        "project_id": project_id,
        "site_url": site_url,
        "status": "updated"
    }
